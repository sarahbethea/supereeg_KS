import os
import time
import multiprocessing
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
from dipy.tracking import utils as tracking_utils
from dipy.data import small_sphere
from dipy.io.stateful_tractogram import StatefulTractogram, Space
from dipy.io.streamline import save_tractogram
import matplotlib.pyplot as plt

# ─────────────────────────────────────────────
# GPU detection — uses CuPy if available,
# falls back to NumPy silently
# ─────────────────────────────────────────────

try:
    import cupy as cp
    _test = cp.zeros(1)   # smoke-test: confirm CUDA is actually working
    del _test
    USE_GPU = True
    print("=" * 60)
    print("GPU detected — matrix operations will run on GPU (CuPy)")
    print(f"  Device : {cp.cuda.runtime.getDeviceProperties(0)['name'].decode()}")
    print("=" * 60)
except Exception:
    cp      = None
    USE_GPU = False
    print("=" * 60)
    print("No GPU / CuPy not installed — running on CPU (NumPy)")
    print("  To enable GPU: pip install cupy-cuda12x  (match your CUDA version)")
    print("=" * 60)


def xp():
    """Return cupy if GPU available, else numpy."""
    return cp if USE_GPU else np


# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

SUBJECT_IDS  = ['100206', '100307', '100610', '101006', '101107']

# Build all paths relative to this script's location
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
DWI_DIR      = os.path.join(BASE_DIR, "DWI")
RESULTS_DIR  = os.path.join(BASE_DIR, "DWI_results")
LOCS_FILE    = os.path.join(BASE_DIR, "supereeg_locs.npy")

# Tractography parameters
SEEDS_PER_VOXEL = 1       # 1 = faster, 2 = denser (use 1 for a first run)
MAX_ANGLE       = 30      # max turning angle in degrees between steps
FA_THRESHOLD    = 0.15    # stop tracking below this GFA value
STEP_SIZE       = 0.5     # step size in mm
MIN_LENGTH      = 20      # discard streamlines shorter than this (mm)
MAX_LENGTH      = 200     # discard streamlines longer than this (mm)
ENDPOINT_RADIUS = 5.0     # mm radius around each electrode for connectivity

# Use all available CPU cores for CSD fitting
N_CORES = multiprocessing.cpu_count()

# ─────────────────────────────────────────────
# Load superEEG electrode locations (shared)
# ─────────────────────────────────────────────

print("=" * 60)
print("Loading superEEG electrode locations...")
locs   = np.load(LOCS_FILE)
n_locs = locs.shape[0]
print(f"  Locations shape : {locs.shape}  (n_electrodes x 3)")
print(f"  MNI x range     : [{locs[:,0].min():.1f}, {locs[:,0].max():.1f}]")
print(f"  MNI y range     : [{locs[:,1].min():.1f}, {locs[:,1].max():.1f}]")
print(f"  MNI z range     : [{locs[:,2].min():.1f}, {locs[:,2].max():.1f}]")
print(f"  CPU cores available : {N_CORES}")


# ─────────────────────────────────────────────
# Helper: build connectivity matrix (vectorized)
# ─────────────────────────────────────────────

def build_connectivity_matrix(streamlines, locs_mm, radius_mm):
    """
    Vectorized connectivity matrix — no Python loops over pairs.

    Key idea: build a boolean touch matrix T of shape (n_electrodes, n_streamlines)
    where T[i, k] = 1 if streamline k's endpoint falls within radius of electrode i.
    Then conn = T @ T.T gives the number of streamlines touching each pair.

    Automatically runs on GPU (CuPy) if available, otherwise NumPy CPU.
    Chunked over electrodes to keep peak RAM/VRAM manageable.
    """
    _xp   = xp()
    n_sl  = len(streamlines)
    n_loc = len(locs_mm)
    r2    = radius_mm ** 2
    backend = "GPU (CuPy)" if USE_GPU else "CPU (NumPy)"

    t0 = time.time()
    print(f"    Extracting endpoints for {n_sl:,} streamlines  [{backend}]...")
    endpoints_A = np.array([s[0]  for s in streamlines], dtype=np.float32)
    endpoints_B = np.array([s[-1] for s in streamlines], dtype=np.float32)

    # Move endpoint arrays to GPU if available
    ep_A = _xp.array(endpoints_A)   # (n_sl, 3)
    ep_B = _xp.array(endpoints_B)   # (n_sl, 3)
    locs_xp = _xp.array(locs_mm.astype(np.float32))

    print(f"    Building touch matrix ({n_loc} electrodes x {n_sl:,} streamlines)...")

    # Process in chunks to limit peak RAM / VRAM
    # GPU can handle larger chunks; CPU uses smaller ones
    CHUNK = 500 if USE_GPU else 100
    touch = _xp.zeros((n_loc, n_sl), dtype=_xp.bool_)

    for start in range(0, n_loc, CHUNK):
        end       = min(start + CHUNK, n_loc)
        loc_chunk = locs_xp[start:end, _xp.newaxis, :]      # (chunk, 1, 3)
        d2_A = _xp.sum((ep_A[_xp.newaxis] - loc_chunk) ** 2, axis=2)  # (chunk, n_sl)
        d2_B = _xp.sum((ep_B[_xp.newaxis] - loc_chunk) ** 2, axis=2)
        touch[start:end] = (d2_A < r2) | (d2_B < r2)

    n_touches = int(touch.sum())
    print(f"    Touch matrix built in {time.time()-t0:.1f}s  "
          f"({n_touches:,} electrode-streamline touches)")

    # conn[i,j] = streamlines touching both electrode i and j
    # This is the expensive step — GPU makes it ~10-20x faster
    print("    Computing connectivity via matrix multiplication...")
    t1      = time.time()
    touch_f = touch.astype(_xp.float32)
    conn_xp = touch_f @ touch_f.T
    _xp.fill_diagonal(conn_xp, 0)
    print(f"    Matrix multiplication done in {time.time()-t1:.1f}s")

    # Move result back to CPU numpy array for saving
    conn = cp.asnumpy(conn_xp) if USE_GPU else conn_xp
    return conn


# ─────────────────────────────────────────────
# Helper: plot and save connectivity matrix
# ─────────────────────────────────────────────

def plot_conn_matrix(conn, subject_id, out_path):
    fig, ax = plt.subplots(figsize=(10, 9))
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
os.makedirs(RESULTS_DIR, exist_ok=True)

for subject_id in SUBJECT_IDS:
    t_subject = time.time()
    print()
    print("=" * 60)
    print(f"Processing subject: {subject_id}")
    print("=" * 60)

    # ── File paths ──────────────────────────────
    dwi_path    = os.path.join(DWI_DIR,     subject_id, "data.nii")
    bval_path   = os.path.join(DWI_DIR,     subject_id, "bvals")
    bvec_path   = os.path.join(DWI_DIR,     subject_id, "bvecs")
    subject_out = os.path.join(RESULTS_DIR, subject_id)
    os.makedirs(subject_out, exist_ok=True)

    # ── Check files exist ───────────────────────
    missing = [p for p in [dwi_path, bval_path, bvec_path] if not os.path.exists(p)]
    if missing:
        for p in missing:
            print(f"  WARNING: File not found, skipping subject — {p}")
        continue

    # ── Load DWI image ───────────────────────────
    print(f"  Loading DWI: {dwi_path}")
    t0     = time.time()
    img    = nib.load(dwi_path)
    data   = img.get_fdata(dtype=np.float32)  # float32 saves ~half the RAM vs float64
    affine = img.affine
    print(f"  Loaded in {time.time()-t0:.1f}s")
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
    print("  Computing brain mask...")
    t0      = time.time()
    b0_idx  = np.where(bvals < 10)[0]
    b0_mean = data[..., b0_idx].mean(axis=-1)
    _, mask = median_otsu(b0_mean, vol_idx=None, median_radius=4, numpass=4)
    print(f"  Brain mask done in {time.time()-t0:.1f}s  "
          f"({mask.sum():,} brain voxels)")

    # ── Fit CSD model (parallelized) ─────────────
    print("  Estimating response function...")
    t0 = time.time()
    response, ratio = auto_response_ssst(gtab, data, roi_radii=10, fa_thr=0.7)
    print(f"  Response eigenvalues    : {response[0]}")
    print(f"  Ratio (target ~0.1–0.3) : {ratio:.4f}")

    print(f"  Fitting CSD model using {N_CORES} CPU cores...")
    t0        = time.time()
    csd_model = ConstrainedSphericalDeconvModel(gtab, response)
    csd_fit   = csd_model.fit(data, mask=mask, num_processes=N_CORES)
    print(f"  CSD fit done in {time.time()-t0:.1f}s")

    # ── GFA map for stopping criterion ───────────
    print("  Computing GFA map...")
    t0        = time.time()
    csa_model = CsaOdfModel(gtab, sh_order=6)
    csa_fit   = csa_model.fit(data, mask=mask)
    gfa       = csa_fit.gfa
    print(f"  GFA done in {time.time()-t0:.1f}s  "
          f"min/max/mean: {gfa.min():.3f}/{gfa.max():.3f}/{gfa.mean():.3f}")

    stopping_criterion = ThresholdStoppingCriterion(gfa, FA_THRESHOLD)

    # ── Seeds ─────────────────────────────────────
    wm_mask = gfa > FA_THRESHOLD
    seeds   = tracking_utils.seeds_from_mask(wm_mask, affine,
                                             density=SEEDS_PER_VOXEL)
    print(f"  White matter voxels : {wm_mask.sum():,}")
    print(f"  Total seeds         : {len(seeds):,}")

    # ── Direction getter ──────────────────────────
    prob_dg = ProbabilisticDirectionGetter.from_shcoeff(
        csd_fit.shm_coeff,
        max_angle=MAX_ANGLE,
        sphere=small_sphere
    )

    # ── Tractography ──────────────────────────────
    print("  Running probabilistic tractography...")
    t0 = time.time()
    streamlines = Streamlines(LocalTracking(
        prob_dg, stopping_criterion, seeds, affine, step_size=STEP_SIZE
    ))
    print(f"  Tractography done in {time.time()-t0:.1f}s  "
          f"({len(streamlines):,} raw streamlines)")

    # ── Length filter ─────────────────────────────
    lengths     = np.array([len(s) * STEP_SIZE for s in streamlines])
    keep        = (lengths >= MIN_LENGTH) & (lengths <= MAX_LENGTH)
    streamlines = Streamlines([s for s, k in zip(streamlines, keep) if k])
    print(f"  After length filter ({MIN_LENGTH}–{MAX_LENGTH} mm) : "
          f"{len(streamlines):,} streamlines")

    # ── Save streamlines ──────────────────────────
    trk_path = os.path.join(subject_out, f"{subject_id}_streamlines.trk")
    sft      = StatefulTractogram(streamlines, img, Space.RASMM)
    save_tractogram(sft, trk_path, bbox_valid_check=False)
    print(f"  Saved streamlines : {trk_path}")

    # ── Connectivity matrix (vectorized) ──────────
    print("  Building structural connectivity matrix (vectorized)...")
    t0   = time.time()
    conn = build_connectivity_matrix(streamlines, locs, ENDPOINT_RADIUS)
    print(f"  Connectivity matrix done in {time.time()-t0:.1f}s")
    print(f"  Matrix shape         : {conn.shape}")
    print(f"  Non-zero entries     : {(conn > 0).sum():,}  "
          f"({100*(conn > 0).mean():.1f}% of pairs connected)")
    print(f"  Max streamline count : {conn.max():.0f}")
    if (conn > 0).any():
        print(f"  Mean (non-zero)      : {conn[conn > 0].mean():.2f}")

    # ── Normalise ─────────────────────────────────
    conn_norm = conn / len(streamlines) if len(streamlines) > 0 else conn
    print(f"  Normalised max       : {conn_norm.max():.6f}")

    # ── Save outputs ──────────────────────────────
    npz_path = os.path.join(subject_out, f"{subject_id}_connectivity.npz")
    np.savez(npz_path,
             conn_matrix=conn,
             conn_matrix_norm=conn_norm,
             locs=locs,
             n_streamlines=np.array(len(streamlines)))
    print(f"  Saved npz  : {npz_path}")

    plot_conn_matrix(conn, subject_id,
                     os.path.join(subject_out, f"{subject_id}_connectivity.png"))

    all_conn_matrices.append(conn_norm)
    print(f"  ✓ Subject {subject_id} complete in {(time.time()-t_subject)/60:.1f} min")


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
          f"({100*(group_conn > 0).mean():.1f}% of pairs)")

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
