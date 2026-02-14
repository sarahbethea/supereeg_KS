"""
Thin HDF5 I/O layer for SuperEEG (replacement for deprecated deepdish).

Use this module instead of deepdish for saving/loading .bo, .mo, and .locs files.
File format is compatible with files written by deepdish so existing data still loads.

See docs/DEEPDISH_PORT_PLAN.md for full implementation plan.
"""

from __future__ import print_function, division, absolute_import

# -----------------------------------------------------------------------------
# aslice: for partial loads, e.g. load(path, group='/data', sel=aslice[i, j])
# -----------------------------------------------------------------------------

class _SliceHelper(object):
    """Use as: io.aslice[sample_inds, loc_inds] -> passed as sel= to load()."""
    def __getitem__(self, index):
        return index

aslice = _SliceHelper()


# -----------------------------------------------------------------------------
# save(path, data, compression='default')
# -----------------------------------------------------------------------------

def save(path, data, compression='default'):
    """
    Save a dict of arrays/DataFrames/lists/scalars to HDF5 (PyTables).

    Uses the same layout as deepdish so files remain compatible.

    Parameters
    ----------
    path : str
        Output file path (e.g. .bo, .mo, .locs).
    data : dict
        String-keyed dict. Values: numpy arrays, pandas DataFrame/Series,
        list, tuple (< 256 len), scalars, None, or nested dicts of same.
    compression : str or tuple
        'default', 'zlib', 'blosc', None, or (lib, level) e.g. ('blosc', 5).
    """
    raise NotImplementedError(
        "supereeg.io.save is not implemented yet. "
        "See docs/DEEPDISH_PORT_PLAN.md. "
        "For now, use deepdish for I/O."
    )


# -----------------------------------------------------------------------------
# load(path, group=None, sel=None, unpack=False)
# -----------------------------------------------------------------------------

def load(path, group=None, sel=None, unpack=False):
    """
    Load from HDF5 (PyTables). Compatible with files written by deepdish.

    Parameters
    ----------
    path : str
        Input file path.
    group : str or list of str or None
        If None, load root. If str (e.g. '/data', '/locs'), load that group.
        If list, load each and return a tuple.
    sel : tuple of slices/indices or None
        When loading a single array group, apply this selection (e.g. from aslice).
    unpack : bool
        If True and root has one key, return that value instead of the dict.

    Returns
    -------
    Loaded structure (dict, array, DataFrame, scalar, etc.)
    """
    raise NotImplementedError(
        "supereeg.io.load is not implemented yet. "
        "See docs/DEEPDISH_PORT_PLAN.md. "
        "For now, use deepdish for I/O."
    )


__all__ = ['save', 'load', 'aslice']
