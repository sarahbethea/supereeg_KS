import os
import numpy as np
import nibabel as nib
from dipy.io.streamline import load_tractogram
from dipy.tracking.streamline import transform_streamlines
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from mpl_toolkits.mplot3d.art3d import Line3DCollection

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

SUBJECT_ID  = '100206'
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
TRK_PATH    = os.path.join(BASE_DIR, "DWI_results", SUBJECT_ID,
                            f"{SUBJECT_ID}_streamlines.trk")
REF_PATH    = os.path.join(BASE_DIR, "DWI", SUBJECT_ID, "data.nii")
OUT_DIR     = os.path.join(BASE_DIR, "DWI_results", SUBJECT_ID)

# How many streamlines to plot — plotting all millions would be slow and illegible
# 5000-10000 gives a nice dense-looking result without being overwhelming
N_STREAMLINES = 8000

# ─────────────────────────────────────────────
# Load streamlines
# ─────────────────────────────────────────────

print("=" * 60)
print(f"Loading streamlines for subject {SUBJECT_ID}...")
sft = load_tractogram(TRK_PATH, REF_PATH)
sft.to_rasmm()   # make sure we're in mm space

streamlines = sft.streamlines
print(f"  Total streamlines loaded : {len(streamlines):,}")

# Randomly subsample for plotting
rng = np.random.default_rng(seed=42)
idx = rng.choice(len(streamlines), size=min(N_STREAMLINES, len(streamlines)),
                 replace=False)
streamlines_plot = [streamlines[i] for i in idx]
print(f"  Subsampled to            : {len(streamlines_plot):,} for plotting")

# ─────────────────────────────────────────────
# Color streamlines by primary direction
# ─────────────────────────────────────────────
# Standard DTI coloring convention:
#   Red   = left-right  (x axis)
#   Green = front-back  (y axis)
#   Blue  = up-down     (z axis)
# Color is determined by the dominant direction of each streamline

def direction_color(streamline):
    """RGB color based on the mean orientation of the streamline."""
    diff = np.diff(streamline, axis=0)
    mean_dir = np.abs(diff).mean(axis=0)
    norm = mean_dir / (mean_dir.sum() + 1e-8)
    return norm   # (r, g, b)

colors = np.array([direction_color(s) for s in streamlines_plot])

# ─────────────────────────────────────────────
# Make 3-panel figure: axial, coronal, sagittal
# ─────────────────────────────────────────────

print("Rendering 3-panel projection plot...")

fig, axes = plt.subplots(1, 3, figsize=(18, 7), facecolor='black')
fig.suptitle(f"White Matter Tractography — Subject {SUBJECT_ID}",
             color='white', fontsize=16, fontweight='bold', y=1.01)

# Each panel projects streamlines onto a 2D plane
# (axial = x/y, coronal = x/z, sagittal = y/z)
views = [
    ("Axial (top-down)",   0, 1),   # x vs y
    ("Coronal (front)",    0, 2),   # x vs z
    ("Sagittal (side)",    1, 2),   # y vs z
]

for ax, (title, dim_x, dim_y) in zip(axes, views):
    ax.set_facecolor('black')

    # Build line segments for this projection
    segments = []
    seg_colors = []
    for sl, col in zip(streamlines_plot, colors):
        pts = sl[:, [dim_x, dim_y]]
        # Split streamline into individual segments for LineCollection
        segs = np.stack([pts[:-1], pts[1:]], axis=1)
        segments.extend(segs)
        seg_colors.extend([col] * len(segs))

    lc = LineCollection(segments, colors=seg_colors,
                        linewidths=0.4, alpha=0.6)
    ax.add_collection(lc)
    ax.autoscale()
    ax.set_aspect('equal')
    ax.set_title(title, color='white', fontsize=13, fontweight='bold')
    ax.tick_params(colors='white', labelsize=9)
    for spine in ax.spines.values():
        spine.set_edgecolor('white')

    dim_labels = ['x (mm)', 'y (mm)', 'z (mm)']
    ax.set_xlabel(dim_labels[dim_x], color='white', fontsize=11)
    ax.set_ylabel(dim_labels[dim_y], color='white', fontsize=11)

plt.tight_layout()
out_path = os.path.join(OUT_DIR, f"{SUBJECT_ID}_tractography_3panel.png")
plt.savefig(out_path, dpi=200, bbox_inches='tight',
            facecolor='black', edgecolor='none')
plt.close()
print(f"  Saved 3-panel plot : {out_path}")

# ─────────────────────────────────────────────
# Also make a single clean axial view for poster
# ─────────────────────────────────────────────

print("Rendering single axial view...")
fig, ax = plt.subplots(figsize=(10, 10), facecolor='black')
ax.set_facecolor('black')

segments  = []
seg_colors = []
for sl, col in zip(streamlines_plot, colors):
    pts  = sl[:, [0, 1]]
    segs = np.stack([pts[:-1], pts[1:]], axis=1)
    segments.extend(segs)
    seg_colors.extend([col] * len(segs))

lc = LineCollection(segments, colors=seg_colors,
                    linewidths=0.5, alpha=0.7)
ax.add_collection(lc)
ax.autoscale()
ax.set_aspect('equal')
ax.set_title(f"White Matter Tractography\nSubject {SUBJECT_ID} — Axial View",
             color='white', fontsize=15, fontweight='bold')
ax.tick_params(colors='white', labelsize=10)
for spine in ax.spines.values():
    spine.set_edgecolor('white')
ax.set_xlabel('x (mm)', color='white', fontsize=12)
ax.set_ylabel('y (mm)', color='white', fontsize=12)

# Add direction color legend
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor=(1,0,0), label='Left–Right (R)'),
    Patch(facecolor=(0,1,0), label='Anterior–Posterior (G)'),
    Patch(facecolor=(0,0,1), label='Superior–Inferior (B)'),
]
ax.legend(handles=legend_elements, loc='lower right',
          facecolor='black', edgecolor='white',
          labelcolor='white', fontsize=10)

plt.tight_layout()
out_path_single = os.path.join(OUT_DIR, f"{SUBJECT_ID}_tractography_axial.png")
plt.savefig(out_path_single, dpi=200, bbox_inches='tight',
            facecolor='black', edgecolor='none')
plt.close()
print(f"  Saved axial plot   : {out_path_single}")

print()
print("=" * 60)
print("Done.")