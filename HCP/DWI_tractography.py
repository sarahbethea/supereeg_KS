import os
import numpy as np
import nibabel as nib
from dipy.io.gradients import read_bvals_bvecs
from dipy.core.gradients import gradient_table
from dipy.segment.mask import median_otsu
from dipy.reconst.csdeconv import ConstrainedSphericalDeconvModel, auto_response_ssst
from dipy.direction import ProbabilisticDirectionGetter
from dipy.tracking.local_tracking import LocalTracking
from dipy.tracking.streamline import Streamlines
from dipy.tracking.stopping_criterion import ThresholdStoppingCriterion
from dipy.reconst.shm import CsaOdfModel
import matplotlib.pyplot as plt

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

SUBJECT_IDS  = ['100206', '100307', '100610', '101006', '101107']
# Build all paths relative to this script's location
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
DWI_DIR      = os.path.join(BASE_DIR, "DWI")
RESULTS_DIR  = os.path.join(BASE_DIR, "DWI_results")
LOCS_FILE    = os.path.join(BASE_DIR, "supereeg_locs.npy")

# Tractography parameters — these can be tuned
SEEDS_PER_VOXEL   = 2      # how many streamlines to seed per white matter voxel
MAX_ANGLE         = 30     # max turning angle in degrees between steps
FA_THRESHOLD      = 0.15   # stop tracking below this FA value (white matter boundary)
STEP_SIZE         = 0.5    # step size in mm
MIN_LENGTH        = 20     # discard streamlines shorter than this (mm)
MAX_LENGTH        = 200    # discard streamlines longer than this (mm)

# Radius (mm) around each electrode to count streamline endpoints
ENDPOINT_RADIUS   = 5.0

# ─────────────────────────────────────────────
# Load superEEG electrode locations (shared)
# ─────────────────────────────────────────────

print("=" * 60)
print("Loading superEEG electrode locations...")
locs = np.load(LOCS_FILE)
n_locs = locs.shape[0]
print(f"  Locations shape : {locs.shape}  (n_electrodes x 3)")
print(f"  MNI x range     : [{locs[:,0].min():.1f}, {locs[:,0].max():.1f}]")
print(f"  MNI y range     : [{locs[:,1].min():.1f}, {locs[:,1].max():.1f}]")
print(f"  MNI z range     : [{locs[:,2].min():.1f}, {locs[:,2].max():.1f}]")

# ─────────────────────────────────────────────
# Helper: convert MNI mm coords → voxel indices
# ─────────────────────────────────────────────

def mni_to_voxel(coords_mm, affine):
    """
    Convert MNI coordinates (N x 3, mm) to voxel indices using
    the inverse of the image affine.
    Returns integer voxel indices (N x 3).
    """
    inv_affine = np.linalg.inv(affine)
    coords_hom = np.hstack([coords_mm, np.ones((len(coords_mm), 1))])
    vox_hom    = (inv_affine @ coords_hom.T).T
    return np.round(vox_hom[:, :3]).astype(int)


# ─────────────────────────────────────────────
# Helper: build connectivity matrix from streamlines
# ─────────────────────────────────────────────

def build_connectivity_matrix(streamlines, locs_mm, affine, vol_shape, radius_mm):
    """
    For each pair of electrode locations (i, j), count streamlines
    whose endpoints both fall within `radius_mm` of locations i and j.

    Returns a symmetric (n_locs x n_locs) matrix of streamline counts.
    """
    n = len(locs_mm)
    conn = np.zeros((n, n), dtype=np.float32)

    # Convert all streamline endpoints to mm (they are already in mm
    # if tracking was run in mm space, which DIPY does by default)
    endpoints_A = np.array([s[0]  for s in streamlines])   # shape (N, 3)
    endpoints_B = np.array([s[-1] for s in streamlines])   # shape (N, 3)

    print(f"    Computing connectivity for {len(streamlines)} streamlines "
          f"and {n} electrode locations...")

    # For each electrode, find which streamline endpoints are within radius
    r2 = radius_mm ** 2
    endpoint_sets = []
    for loc in locs_mm:
        dist2_A = np.sum((endpoints_A - loc) ** 2, axis=1)
        dist2_B = np.sum((endpoints_B - loc) ** 2, axis=1)
        # A streamline "touches" this electrode if either endpoint is within radius
        touches = np.where((dist2_A < r2) | (dist2_B < r2))[0]
        endpoint_sets.append(set(touches.tolist()))

    # Count streamlines connecting each pair
    for i in range(n):
        for j in range(i + 1, n):
            shared = len(endpoint_sets[i] & endpoint_sets[j])
            conn[i, j] = shared
            conn[j, i] = shared

    return conn


# ─────────────────────────────────────────────
# Helper: plot and save connectivity matrix
# ─────────────────────────────────────────────

def plot_conn_matrix(conn, subject_id, out_path):
    fig, ax = plt.subplots(figsize=(10, 9))
    # Log scale helps visualise sparse connectivity matrices
    log_conn = np.log1p(conn)
    im = ax.imshow(log_conn, cmap="hot", interpolation="nearest")
    plt.colorbar(im, ax=ax, label="log(1 + streamline count)")
    ax.set_title(f"Structural Connectivity Matrix — Subject {subject_id}\n"
                 f"{conn.shape[0]} superEEG electrode locations", fontsize=12)
    ax.set_xlabel("Electrode index")
    ax.set_ylabel("Electrode index")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"  Saved plot : {out_path}")


# ─────────────────────────────────────────────
# Per-subject processing
# ─────────────────────────────────────────────

all_conn_matrices = []

for subject_id in SUBJECT_IDS:
    print()
    print("=" * 60)
    print(f"Processing subject: {subject_id}")
    print("=" * 60)

    # ── File paths ──────────────────────────────
    dwi_path   = os.path.join(DWI_DIR,     subject_id, "data.nii")
    bval_path  = os.path.join(DWI_DIR,     subject_id, "bvals")
    bvec_path  = os.path.join(DWI_DIR,     subject_id, "bvecs")
    subject_out = os.path.join(RESULTS_DIR, subject_id)
    os.makedirs(subject_out, exist_ok=True)

    # ── Check files exist ───────────────────────
    for path in [dwi_path, bval_path, bvec_path]:
        if not os.path.exists(path):
            print(f"  WARNING: File not found, skipping — {path}")
            continue

    # ── Load DWI image ───────────────────────────
    print(f"  Loading DWI: {dwi_path}")
    img    = nib.load(dwi_path)
    data   = img.get_fdata()
    affine = img.affine
    print(f"  Image shape       : {data.shape}  (x, y, z, n_gradients)")
    print(f"  Voxel size (mm)   : {img.header.get_zooms()[:3]}")
    print(f"  Affine:\n{affine}")

    # ── Load gradients ───────────────────────────
    bvals, bvecs = read_bvals_bvecs(bval_path, bvec_path)
    gtab = gradient_table(bvals, bvecs)
    print(f"  Number of volumes : {len(bvals)}")
    print(f"  Unique b-values   : {np.unique(np.round(bvals, -2)).astype(int)}")
    print(f"  Number of b0s     : {(bvals < 10).sum()}")

    # ── Brain mask ───────────────────────────────
    print("  Computing brain mask (median Otsu)...")
    # median_otsu works on the mean b0 image
    b0_idx    = np.where(bvals < 10)[0]
    b0_mean   = data[..., b0_idx].mean(axis=-1)
    _, mask   = median_otsu(b0_mean, vol_idx=None, median_radius=4, numpass=4)
    print(f"  Brain voxels      : {mask.sum():,}")

    # ── Fit CSD model ─────────────────────────────
    # CSD handles crossing fibers better than DTI — important for tractography
    print("  Estimating response function (single-shell single-tissue)...")
    response, ratio = auto_response_ssst(gtab, data, roi_radii=10, fa_thr=0.7)
    print(f"  Response function eigenvalues : {response[0]}")
    print(f"  Ratio (should be ~0.1-0.3)    : {ratio:.4f}")

    print("  Fitting CSD model...")
    csd_model = ConstrainedSphericalDeconvModel(gtab, response)
    csd_fit   = csd_model.fit(data, mask=mask)
    print("  CSD model fitted.")

    # ── FA map for stopping criterion ────────────
    # We use a simple CSA ODF model to get the GFA (generalised FA)
    # which is used to stop tracking at grey matter / CSF boundaries
    print("  Computing GFA map for tracking stopping criterion...")
    csa_model = CsaOdfModel(gtab, sh_order=6)
    csa_fit   = csa_model.fit(data, mask=mask)
    gfa       = csa_fit.gfa
    print(f"  GFA min/max/mean  : {gfa.min():.3f} / {gfa.max():.3f} / {gfa.mean():.3f}")

    stopping_criterion = ThresholdStoppingCriterion(gfa, FA_THRESHOLD)

    # ── Seed mask (white matter) ──────────────────
    # Only seed in voxels with high enough GFA (white matter)
    wm_mask = gfa > FA_THRESHOLD
    print(f"  White matter seed voxels : {wm_mask.sum():,}")

    # Generate seeds: SEEDS_PER_VOXEL seeds randomly placed in each WM voxel
    from dipy.tracking import utils as tracking_utils
    seeds = tracking_utils.seeds_from_mask(wm_mask, affine,
                                           density=SEEDS_PER_VOXEL)
    print(f"  Total seeds       : {len(seeds):,}")

    # ── Direction getter (probabilistic CSD) ─────
    from dipy.data import small_sphere
    prob_dg = ProbabilisticDirectionGetter.from_shcoeff(
        csd_fit.shm_coeff,
        max_angle=MAX_ANGLE,
        sphere=small_sphere
    )

    # ── Run tractography ──────────────────────────
    print("  Running probabilistic tractography...")
    streamline_generator = LocalTracking(
        prob_dg,
        stopping_criterion,
        seeds,
        affine,
        step_size=STEP_SIZE
    )
    streamlines = Streamlines(streamline_generator)
    print(f"  Raw streamlines   : {len(streamlines):,}")

    # ── Filter by length ──────────────────────────
    lengths = np.array([len(s) * STEP_SIZE for s in streamlines])
    keep    = (lengths >= MIN_LENGTH) & (lengths <= MAX_LENGTH)
    streamlines = Streamlines([s for s, k in zip(streamlines, keep) if k])
    print(f"  After length filter ({MIN_LENGTH}–{MAX_LENGTH} mm) : {len(streamlines):,}")

    # ── Save streamlines ──────────────────────────
    from dipy.io.stateful_tractogram import StatefulTractogram, Space
    from dipy.io.streamline import save_tractogram
    trk_path = os.path.join(subject_out, f"{subject_id}_streamlines.trk")
    sft = StatefulTractogram(streamlines, img, Space.RASMM)
    save_tractogram(sft, trk_path, bbox_valid_check=False)
    print(f"  Saved streamlines : {trk_path}")

    # ── Build connectivity matrix ─────────────────
    print("  Building structural connectivity matrix...")
    conn = build_connectivity_matrix(
        streamlines, locs, affine, data.shape[:3], ENDPOINT_RADIUS
    )
    print(f"  Connectivity matrix shape : {conn.shape}")
    print(f"  Non-zero entries          : {(conn > 0).sum():,}  "
          f"({100*(conn>0).mean():.1f}% of pairs connected)")
    print(f"  Max streamline count      : {conn.max():.0f}")
    print(f"  Mean (non-zero)           : {conn[conn>0].mean():.2f}")

    # ── Normalise ─────────────────────────────────
    # Divide by total streamlines so matrices are comparable across subjects
    conn_norm = conn / len(streamlines) if len(streamlines) > 0 else conn
    print(f"  Normalised max            : {conn_norm.max():.6f}")

    # ── Save outputs ──────────────────────────────
    npz_path = os.path.join(subject_out, f"{subject_id}_connectivity.npz")
    np.savez(npz_path,
             conn_matrix=conn,
             conn_matrix_norm=conn_norm,
             locs=locs,
             n_streamlines=np.array(len(streamlines)))
    print(f"  Saved npz  : {npz_path}")

    png_path = os.path.join(subject_out, f"{subject_id}_connectivity.png")
    plot_conn_matrix(conn, subject_id, png_path)

    all_conn_matrices.append(conn_norm)


# ─────────────────────────────────────────────
# Group average connectivity matrix
# ─────────────────────────────────────────────

if len(all_conn_matrices) > 1:
    print()
    print("=" * 60)
    print("Computing group average connectivity matrix...")
    group_conn = np.mean(np.stack(all_conn_matrices, axis=0), axis=0)
    print(f"  Subjects included  : {len(all_conn_matrices)}")
    print(f"  Group conn shape   : {group_conn.shape}")
    print(f"  Group conn max     : {group_conn.max():.6f}")
    print(f"  Non-zero entries   : {(group_conn > 0).sum():,}  "
          f"({100*(group_conn>0).mean():.1f}% of pairs)")

    group_npz = os.path.join(RESULTS_DIR, "group_average_connectivity.npz")
    np.savez(group_npz,
             conn_matrix=group_conn,
             locs=locs,
             subject_ids=np.array(SUBJECT_IDS))
    print(f"  Saved npz  : {group_npz}")

    plot_conn_matrix(group_conn, "GROUP_AVERAGE",
                     os.path.join(RESULTS_DIR, "group_average_connectivity.png"))

print()
print("=" * 60)
print("Done.")