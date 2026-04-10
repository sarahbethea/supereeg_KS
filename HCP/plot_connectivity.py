import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

SUBJECT_IDS = ['100206', '100307', '100610', '101006', '101107']

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "DWI_results")


# ─────────────────────────────────────────────
# Plotting function — poster quality
# ─────────────────────────────────────────────

def plot_conn_matrix_poster(conn, subject_id, out_path):
    """
    High-contrast connectivity matrix plot suitable for a poster.

    Key improvements over the original dark plot:
    - Percentile-based color scaling so rare bright values don't crush everything else
    - Power-norm stretch to pull out structure in the low end
    - Cleaner colormap (inferno reads better on white poster backgrounds than hot)
    - Larger fonts, thicker colorbar, clear title
    """
    fig, ax = plt.subplots(figsize=(10, 9))

    # Log-transform to compress the dynamic range
    log_conn = np.log1p(conn)

    # Clip color scale at 99th percentile so outliers don't crush the rest
    vmin = 0
    vmax = np.percentile(log_conn[log_conn > 0], 99) if (log_conn > 0).any() else 1

    # White (no connection) → red (strong connection)
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "white_red", ["white", "red"]
    )

    im = ax.imshow(log_conn, cmap=cmap, vmin=vmin, vmax=vmax,
                   interpolation="nearest")

    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("log(1 + streamline count)", fontsize=13)
    cbar.ax.tick_params(labelsize=11)

    n = conn.shape[0]
    ax.set_title(f"Structural Connectivity Matrix — Subject {subject_id}\n"
                 f"{n} superEEG electrode locations", fontsize=14, fontweight='bold')
    ax.set_xlabel("Electrode index", fontsize=13)
    ax.set_ylabel("Electrode index", fontsize=13)
    ax.tick_params(labelsize=11)

    plt.tight_layout()
    plt.savefig(out_path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  Saved: {out_path}")


# ─────────────────────────────────────────────
# Also make a group comparison figure
# ─────────────────────────────────────────────

def plot_group_comparison(matrices, subject_ids, out_path):
    """
    Side-by-side subplots of all subjects — useful for a poster panel.
    """
    n_subj = len(matrices)
    fig, axes = plt.subplots(1, n_subj, figsize=(5 * n_subj, 5))
    if n_subj == 1:
        axes = [axes]

    # Shared color scale across all subjects for fair comparison
    all_vals = np.concatenate([np.log1p(m).ravel() for m in matrices])
    vmax     = np.percentile(all_vals[all_vals > 0], 99) if (all_vals > 0).any() else 1
    cmap     = mcolors.LinearSegmentedColormap.from_list("white_red", ["white", "red"])

    for ax, conn, sid in zip(axes, matrices, subject_ids):
        im = ax.imshow(np.log1p(conn), cmap=cmap, vmin=0, vmax=vmax,
                       interpolation="nearest")
        ax.set_title(f"Subject\n{sid}", fontsize=11, fontweight='bold')
        ax.set_xlabel("Electrode", fontsize=9)
        ax.set_ylabel("Electrode", fontsize=9)
        ax.tick_params(labelsize=8)

    # Single shared colorbar on the right
    fig.subplots_adjust(right=0.88)
    cbar_ax = fig.add_axes([0.91, 0.15, 0.02, 0.7])
    cbar    = fig.colorbar(im, cax=cbar_ax)
    cbar.set_label("log(1 + streamline count)", fontsize=11)

    fig.suptitle("Structural Connectivity — All Subjects", fontsize=14,
                 fontweight='bold', y=1.01)
    plt.savefig(out_path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  Saved group comparison: {out_path}")


# ─────────────────────────────────────────────
# Main: load and replot
# ─────────────────────────────────────────────

print("=" * 60)
print("Replotting connectivity matrices...")
print("=" * 60)

loaded_matrices = []
loaded_ids      = []

for subject_id in SUBJECT_IDS:
    npz_path = os.path.join(RESULTS_DIR, subject_id,
                            f"{subject_id}_connectivity.npz")
    if not os.path.exists(npz_path):
        print(f"  WARNING: No saved matrix found for {subject_id}, skipping — {npz_path}")
        continue

    print(f"\nSubject {subject_id}")
    data = np.load(npz_path)
    conn = data['conn_matrix']
    print(f"  Matrix shape     : {conn.shape}")
    print(f"  Non-zero entries : {(conn > 0).sum():,}  "
          f"({100*(conn > 0).mean():.1f}%)")
    print(f"  Max value        : {conn.max():.0f}")
    print(f"  99th percentile  : {np.percentile(conn[conn>0], 99):.1f}"
          if (conn > 0).any() else "  No connected pairs")

    out_path = os.path.join(RESULTS_DIR, subject_id,
                            f"{subject_id}_connectivity_poster.png")
    plot_conn_matrix_poster(conn, subject_id, out_path)

    loaded_matrices.append(conn)
    loaded_ids.append(subject_id)

# Group average
group_npz = os.path.join(RESULTS_DIR, "group_average_connectivity.npz")
if os.path.exists(group_npz):
    print(f"\nGroup average")
    gdata      = np.load(group_npz)
    group_conn = gdata['conn_matrix']
    plot_conn_matrix_poster(group_conn, "GROUP_AVERAGE",
                            os.path.join(RESULTS_DIR,
                                         "group_average_connectivity_poster.png"))

# Side-by-side comparison panel
if len(loaded_matrices) > 1:
    print(f"\nGenerating group comparison panel...")
    plot_group_comparison(loaded_matrices, loaded_ids,
                          os.path.join(RESULTS_DIR, "all_subjects_comparison.png"))

print()
print("=" * 60)
print("Done. Look for files ending in '_poster.png'")
print("=" * 60)