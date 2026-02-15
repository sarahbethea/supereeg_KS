import numpy as np
import scipy.io as sio
from supereeg import Brain  # or wherever Brain is imported from
from supereeg.io import save, load
import h5py

path = "gf_joystick.mat"

mat = sio.loadmat(path, squeeze_me=True, struct_as_record=False)

data = mat["data"].astype(np.float32)          # optional: float for downstream math
locs_tal = mat["electrodes"].astype(np.float64)
subject = mat["subject"]

meta = {
    "subject": subject,
    "source": "kai_miller",
    "coord_space": "talairach",
    "has_behavior": True,
}

# bo = Brain(
#     data=data,
#     locs=locs_tal,
#     sessions=None,        # single session
#     sample_rate=1000,
#     meta=meta,
#     filter=None,          # optional while debugging
# )

# bo.info()


# # Where do we store the brain objects? 
# # Where are model objects and brain objects stored?
# # should we just create a BO for each patient for each task?

fname = 'saved_brain.bo'


# bo.save(fname, compression='gzip')  

bo2 = Brain(**load(fname))
bo2.info()
print(bo2.get_locs())





