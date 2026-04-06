import numpy as np
import nibabel as nib
from dipy.io.gradients import read_bvals_bvecs
from scipy.spatial.distance import cdist
import matplotlib.pyplot as plt
import pandas as pd


# ─────────────────────────────────────────────
# Utility functions
# ─────────────────────────────────────────────

def voxel_to_mni(voxel_indices, affine):
    """
    Convert an array of voxel indices (N, 3) to MNI coordinates (N, 3)
    using the image affine matrix.

    Parameters
    ----------
    voxel_indices : np.ndarray, shape (N, 3)
        Integer ijk voxel coordinates.
    affine : np.ndarray, shape (4, 4)
        Affine matrix from the NIfTI image (img.affine).

    Returns
    -------
    mni_coords : np.ndarray, shape (N, 3)
        Corresponding MNI (x, y, z) coordinates in mm.
    """
    # Homogeneous coordinates: append a column of ones
    n = voxel_indices.shape[0]
    homogeneous = np.hstack([voxel_indices, np.ones((n, 1))])   # (N, 4)
    mni_coords = (affine @ homogeneous.T).T                      # (N, 4)
    return mni_coords[:, :3]                                     # drop homogeneous dim


def pairwise_distance_matrix(coords):
    """
    Compute the pairwise Euclidean distance matrix for a set of coordinates.

    Parameters
    ----------
    coords : np.ndarray, shape (N, 3)
        MNI (or any) coordinates.

    Returns
    -------
    dist_mat : np.ndarray, shape (N, N)
    """
    return cdist(coords, coords, metric="euclidean")


def plot_matrix(mat, labels=None, title="Matrix", cmap="coolwarm",
                vmin=None, vmax=None, out_file=None):
    plt.figure(figsize=(8, 7))
    plt.imshow(mat, cmap=cmap, vmin=vmin, vmax=vmax, interpolation="nearest")
    plt.colorbar()
    if labels is not None:
        plt.xticks(range(len(labels)), labels, rotation=90, fontsize=6)
        plt.yticks(range(len(labels)), labels, fontsize=6)
    plt.title(title)
    plt.tight_layout()
    if out_file:
        plt.savefig(out_file, dpi=150)
        print(f"Saved figure: {out_file}")
    plt.show()


def save_matrix_csv(mat, labels, out_file):
    df = pd.DataFrame(mat, index=labels, columns=labels)
    df.to_csv(out_file)
    print(f"Saved: {out_file}")


# ─────────────────────────────────────────────
# File paths  — edit these
# ─────────────────────────────────────────────

dwi_path  = "100206/data.nii"
bval_path = "100206/bvals"
bvec_path = "100206/bvecs"

N_VOXELS  = 2000   # keep small for a first run
B0_THRESH = 50     # volumes with bval <= this are treated as b0

# ─────────────────────────────────────────────
# Load image + gradients
# ─────────────────────────────────────────────

img    = nib.load(dwi_path)
data   = img.get_fdata()          # (X, Y, Z, N_volumes)
affine = img.affine               # ← we need this for voxel→MNI conversion
print("DWI shape :", data.shape)
print("Affine    :\n", affine)

bvals, bvecs = read_bvals_bvecs(bval_path, bvec_path)
print("bvals shape:", bvals.shape)
print("bvecs shape:", bvecs.shape)

# ─────────────────────────────────────────────
# Sanity checks
# ─────────────────────────────────────────────

assert data.ndim == 4,                             "DWI image must be 4D"
assert data.shape[3] == len(bvals),                "Volumes must match bvals"
assert bvecs.shape[0] == len(bvals),               "bvecs must match bvals"

# ─────────────────────────────────────────────
# Keep only diffusion-weighted volumes (b > 50)
# ─────────────────────────────────────────────

keep_vols = bvals > B0_THRESH
data      = data[..., keep_vols]
print(f"Using {data.shape[3]} diffusion-weighted volumes")

# ─────────────────────────────────────────────
# Brain mask from mean signal
# ─────────────────────────────────────────────

mean_img = data.mean(axis=3)
mask     = mean_img > 100          # adjust if needed
print(f"Masked voxels: {mask.sum()}")

# ─────────────────────────────────────────────
# Extract voxel signals & voxel indices. This is where we have to choose how to sample. Distance matrix vs correlation require different methods
# ─────────────────────────────────────────────

all_voxel_indices = np.argwhere(mask)              # (n_all_voxels, 3)
X_all             = data[mask]                     # (n_all_voxels, n_volumes)

# Subsample for speed
X             = X_all[:N_VOXELS]                   # (N_VOXELS, n_volumes)
voxel_indices = all_voxel_indices[:N_VOXELS]       # (N_VOXELS, 3)




# ─────────────────────────────────────────────
# Voxel indices  →  MNI coordinates  ← KEY STEP
# ─────────────────────────────────────────────

mni_coords = voxel_to_mni(voxel_indices, affine)   # (N_VOXELS, 3)
print(f"MNI coords shape : {mni_coords.shape}")
print(f"MNI range x: [{mni_coords[:,0].min():.1f}, {mni_coords[:,0].max():.1f}]")
print(f"MNI range y: [{mni_coords[:,1].min():.1f}, {mni_coords[:,1].max():.1f}]")
print(f"MNI range z: [{mni_coords[:,2].min():.1f}, {mni_coords[:,2].max():.1f}]")

# ─────────────────────────────────────────────
# Correlation matrix
# ─────────────────────────────────────────────

corr = np.corrcoef(X)
print(f"Correlation matrix shape: {corr.shape}")
print(f"corr  min={corr.min():.3f}  max={corr.max():.3f}  "
      f"mean={corr.mean():.3f}  std={corr.std():.3f}")
print(f"Any NaNs in corr? {np.isnan(corr).any()}")

# ─────────────────────────────────────────────
# Euclidean distance matrix in MNI space
# ─────────────────────────────────────────────

dist_mat = pairwise_distance_matrix(mni_coords)
print(f"Distance matrix shape: {dist_mat.shape}")
print(f"Distance range: [{dist_mat.min():.1f}, {dist_mat.max():.1f}] mm")

# ─────────────────────────────────────────────
# Save outputs
# ─────────────────────────────────────────────

np.save("subject02_corr.npy",         corr)
np.save("subject02_voxel_indices.npy", voxel_indices)
print(corr.shape)
print(voxel_indices.shape)
print(mni_coords.shape)
np.save("subject02_mni_coords.npy",    mni_coords)
np.save("subject02_dist_mat.npy",      dist_mat)
print("Saved correlation matrix, voxel indices, MNI coords, and distance matrix.")

# ─────────────────────────────────────────────
# Plots
# ─────────────────────────────────────────────

plot_matrix(
    corr,
    title="Voxelwise Correlation Matrix (DWI)",
    cmap="coolwarm", vmin=-1, vmax=1,
    out_file="subject01_corr_matrix.png"
)

plot_matrix(
    dist_mat,
    title="Pairwise Euclidean Distance in MNI Space (mm)",
    cmap="viridis",
    out_file="subject01_dist_matrix.png"
)



