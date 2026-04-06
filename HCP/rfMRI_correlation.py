import os
import numpy as np
import nibabel as nib
import pandas as pd
import matplotlib.pyplot as plt
from nilearn import datasets
from nilearn.maskers import NiftiLabelsMasker

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

SUBJECT_IDS = ['100206', '100307', '100610', '101006', '101107']
FMRI_DIR    = "rfMRI"
RESULTS_DIR = "results"
FMRI_FILE   = "rfMRI_REST1_LR_hp2000_clean_rclean_tclean.nii"
N_ROIS      = 200   # Schaefer atlas size — change to 100, 300, 400, 500, 600, 800, 1000 if needed

# ─────────────────────────────────────────────
# Load atlas once (shared across all subjects)
# ─────────────────────────────────────────────

print("=" * 60)
print("Loading Schaefer atlas...")
atlas = datasets.fetch_atlas_schaefer_2018(n_rois=N_ROIS, resolution_mm=2)
atlas_img  = atlas.maps
roi_labels = [label.decode() if isinstance(label, bytes) else label
              for label in atlas.labels]
roi_labels = [l for l in roi_labels if l != 'Background']
print(f"Atlas: Schaefer 2018, {N_ROIS} ROIs")
print(f"Atlas image shape: {nib.load(atlas_img).shape}")
print(f"Number of ROI labels: {len(roi_labels)}")
print(f"First 5 labels: {roi_labels[:5]}")
print(f"Last 5 labels:  {roi_labels[-5:]}")

# ─────────────────────────────────────────────
# Set up masker once (shared across all subjects)
# ─────────────────────────────────────────────

masker = NiftiLabelsMasker(
    labels_img=atlas_img,
    standardize='zscore_sample',       # z-score each ROI timeseries (zero mean, unit variance)
    memory_level=1,         # cache intermediate results
    verbose=0
)

# ─────────────────────────────────────────────
# Helper: plot and save correlation matrix
# ─────────────────────────────────────────────

def plot_corr_matrix(corr, labels, subject_id, out_path):
    fig, ax = plt.subplots(figsize=(12, 10))
    im = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1, interpolation="nearest")
    plt.colorbar(im, ax=ax, label="Pearson r")

    # Only show every Nth label to avoid overcrowding
    tick_step = max(1, len(labels) // 20)
    ticks = range(0, len(labels), tick_step)
    ax.set_xticks(ticks)
    ax.set_yticks(ticks)
    ax.set_xticklabels([labels[i] for i in ticks], rotation=90, fontsize=6)
    ax.set_yticklabels([labels[i] for i in ticks], fontsize=6)

    ax.set_title(f"Functional Connectivity Matrix — Subject {subject_id}\n"
                 f"Schaefer {N_ROIS} ROIs, rfMRI_REST1_LR", fontsize=12)
    ax.set_xlabel("ROI")
    ax.set_ylabel("ROI")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"  Saved plot: {out_path}")


# ─────────────────────────────────────────────
# Per-subject processing
# ─────────────────────────────────────────────

all_corr_matrices = []   # collect for group average

for subject_id in SUBJECT_IDS:
    print()
    print("=" * 60)
    print(f"Processing subject: {subject_id}")
    print("=" * 60)

    # ---- file paths ----
    fmri_path   = os.path.join(FMRI_DIR, subject_id, FMRI_FILE)
    subject_out = os.path.join(RESULTS_DIR, subject_id)
    os.makedirs(subject_out, exist_ok=True)

    # ---- check file exists ----
    if not os.path.exists(fmri_path):
        print(f"  WARNING: File not found, skipping — {fmri_path}")
        continue

    # ---- load and inspect image ----
    print(f"  Loading: {fmri_path}")
    img = nib.load(fmri_path)
    print(f"  Image shape       : {img.shape}")
    print(f"  Voxel size (mm)   : {img.header.get_zooms()[:3]}")
    print(f"  TR (s)            : {img.header.get_zooms()[3]:.4f}")
    print(f"  Number of volumes : {img.shape[3]}")
    print(f"  Affine:\n{img.affine}")

    # ---- MNI coordinate range sanity check ----
    # Sample corner voxels to verify MNI space
    shape = img.shape[:3]
    corners = np.array([
        [0,         0,         0        ],
        [shape[0]-1, 0,         0        ],
        [0,         shape[1]-1, 0        ],
        [0,         0,         shape[2]-1],
        [shape[0]-1, shape[1]-1, shape[2]-1],
    ])
    hom      = np.hstack([corners, np.ones((len(corners), 1))])
    mni_cors = (img.affine @ hom.T).T[:, :3]
    print(f"  MNI x range (mm)  : [{mni_cors[:,0].min():.1f}, {mni_cors[:,0].max():.1f}]")
    print(f"  MNI y range (mm)  : [{mni_cors[:,1].min():.1f}, {mni_cors[:,1].max():.1f}]")
    print(f"  MNI z range (mm)  : [{mni_cors[:,2].min():.1f}, {mni_cors[:,2].max():.1f}]")

    # ---- extract ROI timeseries ----
    print(f"  Extracting ROI timeseries ({N_ROIS} ROIs)...")
    roi_timeseries = masker.fit_transform(fmri_path)   # shape: (n_timepoints, n_rois)
    print(f"  ROI timeseries shape : {roi_timeseries.shape}  (timepoints × ROIs)")
    print(f"  Signal min  : {roi_timeseries.min():.4f}")
    print(f"  Signal max  : {roi_timeseries.max():.4f}")
    print(f"  Signal mean : {roi_timeseries.mean():.4f}")
    print(f"  Signal std  : {roi_timeseries.std():.4f}")
    print(f"  Any NaNs?   : {np.isnan(roi_timeseries).any()}")

    # ---- compute correlation matrix ----
    corr = np.corrcoef(roi_timeseries.T)   # shape: (n_rois, n_rois)
    print(f"  Correlation matrix shape : {corr.shape}")
    print(f"  Corr min    : {corr.min():.4f}")
    print(f"  Corr max    : {corr.max():.4f}")
    print(f"  Corr mean   : {corr.mean():.4f}  (expected ~0.0–0.3 for resting state)")
    print(f"  Corr std    : {corr.std():.4f}")
    print(f"  Any NaNs?   : {np.isnan(corr).any()}")

    # ---- save outputs ----
    npz_path = os.path.join(subject_out, f"{subject_id}_corr_matrix.npz")
    csv_path = os.path.join(subject_out, f"{subject_id}_corr_matrix.csv")
    png_path = os.path.join(subject_out, f"{subject_id}_corr_matrix.png")

    # npz: bundles corr matrix + labels together
    np.savez(npz_path,
             corr_matrix=corr,
             roi_labels=np.array(roi_labels))
    print(f"  Saved npz   : {npz_path}")

    # csv: human readable
    df = pd.DataFrame(corr, index=roi_labels, columns=roi_labels)
    df.to_csv(csv_path)
    print(f"  Saved csv   : {csv_path}")

    # png: visualization
    plot_corr_matrix(corr, roi_labels, subject_id, png_path)

    all_corr_matrices.append(corr)


# ─────────────────────────────────────────────
# Group average correlation matrix
# ─────────────────────────────────────────────

if len(all_corr_matrices) > 1:
    print()
    print("=" * 60)
    print("Computing group average correlation matrix...")
    group_corr = np.mean(np.stack(all_corr_matrices, axis=0), axis=0)
    print(f"  Subjects included : {len(all_corr_matrices)}")
    print(f"  Group corr shape  : {group_corr.shape}")
    print(f"  Group corr mean   : {group_corr.mean():.4f}")
    print(f"  Group corr std    : {group_corr.std():.4f}")

    # save group average
    group_npz = os.path.join(RESULTS_DIR, "group_average_corr.npz")
    group_csv = os.path.join(RESULTS_DIR, "group_average_corr.csv")
    group_png = os.path.join(RESULTS_DIR, "group_average_corr.png")

    np.savez(group_npz,
             corr_matrix=group_corr,
             roi_labels=np.array(roi_labels),
             subject_ids=np.array(SUBJECT_IDS))
    print(f"  Saved npz   : {group_npz}")

    df_group = pd.DataFrame(group_corr, index=roi_labels, columns=roi_labels)
    df_group.to_csv(group_csv)
    print(f"  Saved csv   : {group_csv}")

    plot_corr_matrix(group_corr, roi_labels, "GROUP_AVERAGE", group_png)

print()
print("=" * 60)
print("Done.")