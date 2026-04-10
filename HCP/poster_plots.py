import os
import numpy as np
import nibabel as nib
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from nilearn.maskers import NiftiSpheresMasker

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

SUBJECT_IDS  = ['100206', '100307', '100610', '101006', '101107']

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
FMRI_DIR     = os.path.join(BASE_DIR, "rfMRI")
RESULTS_DIR  = os.path.join(BASE_DIR, "results")
LOCS_FILE    = os.path.join(BASE_DIR, "supereeg_locs.npy")
FMRI_FILE    = "rfMRI_REST1_LR_hp2000_clean_rclean_tclean.nii"

SPHERE_RADIUS = 4.0   # mm — matches DWI endpoint radius, good spatial specificity

# ─────────────────────────────────────────────
# Shared poster plot style
# ─────────────────────────────────────────────

CMAP       = "RdBu_r"
VMIN, VMAX = -1.0, 1.0
TITLE_FS   = 14
LABEL_FS   = 12
TICK_FS    = 10
DPI        = 200


def plot_corr_matrix_poster(corr, title, xlabel, ylabel, out_path,
                             xtick_labels=None):
    """
    Unified poster-quality correlation matrix plot.
    Identical style for both Schaefer and superEEG locs plots.
    """
    fig, ax = plt.subplots(figsize=(11, 10), facecolor='white')

    im = ax.imshow(corr, cmap=CMAP, vmin=VMIN, vmax=VMAX,
                   interpolation="nearest", aspect='auto')

    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Pearson r", fontsize=LABEL_FS)
    cbar.ax.tick_params(labelsize=TICK_FS)

    if xtick_labels is not None:
        # Named ROI labels (Schaefer)
        tick_step = max(1, len(xtick_labels) // 20)
        ticks = list(range(0, len(xtick_labels), tick_step))
        ax.set_xticks(ticks)
        ax.set_yticks(ticks)
        ax.set_xticklabels([xtick_labels[i] for i in ticks],
                           rotation=90, fontsize=7)
        ax.set_yticklabels([xtick_labels[i] for i in ticks], fontsize=7)
    else:
        # Numeric index ticks (superEEG locs)
        n     = corr.shape[0]
        ticks = np.linspace(0, n - 1, 6).astype(int)
        ax.set_xticks(ticks)
        ax.set_yticks(ticks)
        ax.set_xticklabels(ticks, fontsize=TICK_FS)
        ax.set_yticklabels(ticks, fontsize=TICK_FS)

    ax.set_title(title, fontsize=TITLE_FS, fontweight='bold', pad=12)
    ax.set_xlabel(xlabel, fontsize=LABEL_FS, labelpad=8)
    ax.set_ylabel(ylabel, fontsize=LABEL_FS, labelpad=8)

    plt.tight_layout()
    plt.savefig(out_path, dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  Saved: {out_path}")


# ─────────────────────────────────────────────
# Plot 1 — Schaefer group average (already computed)
# ─────────────────────────────────────────────

print("=" * 60)
print("Plot 1: Schaefer functional connectivity matrix")
print("=" * 60)

schaefer_npz = os.path.join(RESULTS_DIR, "group_average_corr.npz")
if not os.path.exists(schaefer_npz):
    print(f"  ERROR: File not found — {schaefer_npz}")
else:
    data          = np.load(schaefer_npz, allow_pickle=True)
    schaefer_corr = data['corr_matrix']
    roi_labels    = [str(l) for l in data['roi_labels']]
    print(f"  Matrix shape : {schaefer_corr.shape}")
    print(f"  ROI labels   : {len(roi_labels)}")

    plot_corr_matrix_poster(
        corr         = schaefer_corr,
        title        = "Functional Connectivity Matrix — Group Average\nSchaefer 200 ROIs, rfMRI REST1 LR",
        xlabel       = "ROI",
        ylabel       = "ROI",
        out_path     = os.path.join(RESULTS_DIR, "poster_schaefer_corr.png"),
        xtick_labels = roi_labels,
    )


# ─────────────────────────────────────────────
# Plot 2 — superEEG locs mean correlation
# Sample fMRI signal at each electrode location
# ─────────────────────────────────────────────

print()
print("=" * 60)
print("Plot 2: superEEG locs mean functional connectivity matrix")
print("=" * 60)

print("Loading superEEG electrode locations...")
locs   = np.load(LOCS_FILE)
n_locs = locs.shape[0]
print(f"  Locations: {locs.shape}")

# NiftiSpheresMasker samples a sphere around each MNI coordinate
masker = NiftiSpheresMasker(
    seeds         = locs,
    radius        = 6.0,   # increased from 4mm — ensures boundary locations catch voxels
    standardize   = 'zscore_sample',
    allow_overlap = True,
    verbose       = 0
)

all_corr_matrices = []

for subject_id in SUBJECT_IDS:
    fmri_path = os.path.join(FMRI_DIR, subject_id, FMRI_FILE)
    if not os.path.exists(fmri_path):
        print(f"  WARNING: fMRI file not found, skipping — {fmri_path}")
        continue

    print(f"  Subject {subject_id}...")
    timeseries = masker.fit_transform(fmri_path)   # (n_timepoints, n_locs)
    print(f"    Timeseries shape : {timeseries.shape}")

    # Zero out any NaN columns (electrode locations outside the brain)
    nan_cols = np.isnan(timeseries).any(axis=0)
    if nan_cols.any():
        print(f"    NaN locations    : {nan_cols.sum()} zeroed (outside brain)")
        timeseries[:, nan_cols] = 0.0

    corr = np.corrcoef(timeseries.T)
    print(f"    Corr range       : [{corr.min():.3f}, {corr.max():.3f}]")
    all_corr_matrices.append(corr)

out_npz = os.path.join(RESULTS_DIR, "supereeg_locs_mean_corr.npz")

if os.path.exists(out_npz):
    print(f"  Found existing matrix, loading from {out_npz}")
    mean_corr = np.load(out_npz)['corr_matrix']
    print(f"  Mean corr shape : {mean_corr.shape}")
    plot_corr_matrix_poster(
        corr     = mean_corr,
        title    = f"Mean Functional Connectivity Matrix — Group Average\n"
                   f"{n_locs} superEEG Electrode Locations, rfMRI REST1 LR",
        xlabel   = "Electrode index",
        ylabel   = "Electrode index",
        out_path = os.path.join(RESULTS_DIR, "poster_supereeg_locs_corr.png"),
    )
else:
    if not all_corr_matrices:
        print("  ERROR: No subjects processed successfully.")
    else:
        print(f"\n  Computing mean across {len(all_corr_matrices)} subjects...")
        mean_corr = np.mean(np.stack(all_corr_matrices, axis=0), axis=0)
        np.fill_diagonal(mean_corr, 1.0)
        print(f"  Mean corr shape : {mean_corr.shape}")
        print(f"  Mean corr range : [{mean_corr.min():.3f}, {mean_corr.max():.3f}]")

        np.savez(out_npz,
                 corr_matrix = mean_corr,
                 locs        = locs,
                 subject_ids = np.array(SUBJECT_IDS))
        print(f"  Saved npz: {out_npz}")

        plot_corr_matrix_poster(
            corr     = mean_corr,
            title    = f"Mean Functional Connectivity Matrix — Group Average\n"
                       f"{n_locs} superEEG Electrode Locations, rfMRI REST1 LR",
            xlabel   = "Electrode index",
            ylabel   = "Electrode index",
            out_path = os.path.join(RESULTS_DIR, "poster_supereeg_locs_corr.png"),
        )

print()
print("=" * 60)
print("Done. Poster plots saved to HCP/results/")
print("  poster_schaefer_corr.png")
print("  poster_supereeg_locs_corr.png")
print("=" * 60)