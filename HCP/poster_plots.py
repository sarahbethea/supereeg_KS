import os
import numpy as np
import matplotlib.pyplot as plt
from nilearn.maskers import NiftiSpheresMasker
from nilearn.connectome import ConnectivityMeasure

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

SUBJECT_IDS   = ['100206', '100307', '100610', '101006', '101107']

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
FMRI_DIR      = os.path.join(BASE_DIR, "rfMRI")
RESULTS_DIR   = os.path.join(BASE_DIR, "results")
LOCS_FILE     = os.path.join(BASE_DIR, "supereeg_locs.npy")
FMRI_FILE     = "rfMRI_REST1_LR_hp2000_clean_rclean_tclean.nii"

SPHERE_RADIUS = 32.0   # matches teammate's radius
TITLE_FS      = 14
LABEL_FS      = 12
TICK_FS       = 10
DPI           = 200


# ─────────────────────────────────────────────
# Plotting — pure matplotlib, same style for both plots
# ─────────────────────────────────────────────

def plot_corr_matrix_poster(corr, title, xlabel, ylabel, out_path,
                             xtick_labels=None):
    fig, ax = plt.subplots(figsize=(11, 10), facecolor='white')

    im = ax.imshow(corr, vmin=-1.0, vmax=1.0,
                   interpolation='nearest', aspect='auto')

    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Pearson r", fontsize=LABEL_FS)
    cbar.ax.tick_params(labelsize=TICK_FS)

    if xtick_labels is not None:
        tick_step = max(1, len(xtick_labels) // 20)
        ticks     = list(range(0, len(xtick_labels), tick_step))
        labels    = [xtick_labels[i] for i in ticks]
        ax.set_xticks(ticks)
        ax.set_yticks(ticks)
        ax.set_xticklabels(labels, rotation=90,  ha='right', fontsize=8)
        ax.set_yticklabels(labels, rotation=0,   ha='right', fontsize=8)
    else:
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
# ─────────────────────────────────────────────

print()
print("=" * 60)
print("Plot 2: superEEG locs mean functional connectivity matrix")
print("=" * 60)

locs   = np.load(LOCS_FILE)
n_locs = locs.shape[0]
print(f"  Locations: {locs.shape}")

out_npz = os.path.join(RESULTS_DIR, "supereeg_locs_mean_corr.npz")

# ── If already computed, just replot ──────────
if os.path.exists(out_npz):
    print(f"  Found existing matrix — skipping computation, replotting...")
    mean_corr = np.load(out_npz)['corr_matrix']
    print(f"  Mean corr shape : {mean_corr.shape}")

# ── Otherwise compute from scratch ────────────
else:
    print("  Computing from fMRI data...")

    masker = NiftiSpheresMasker(
        seeds         = locs,
        radius        = SPHERE_RADIUS,
        detrend       = True,
        standardize   = True,
        allow_overlap = True,
        verbose       = 0
    )
    correlation_measure = ConnectivityMeasure(kind='correlation')
    all_corr_matrices   = []

    for subject_id in SUBJECT_IDS:
        fmri_path = os.path.join(FMRI_DIR, subject_id, FMRI_FILE)
        if not os.path.exists(fmri_path):
            print(f"  WARNING: fMRI file not found, skipping — {fmri_path}")
            continue

        print(f"  Subject {subject_id}...")
        timeseries = masker.fit_transform(fmri_path)
        print(f"    Timeseries shape : {timeseries.shape}")

        corr = correlation_measure.fit_transform([timeseries])[0]
        print(f"    Corr range       : [{corr.min():.3f}, {corr.max():.3f}]")
        all_corr_matrices.append(corr)

    if not all_corr_matrices:
        print("  ERROR: No subjects processed.")
        exit(1)

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
               f"{mean_corr.shape[0]} superEEG Electrode Locations, rfMRI REST1 LR",
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