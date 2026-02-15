"""
Thin HDF5 I/O layer for SuperEEG (replacement for deprecated deepdish).

Use this module instead of deepdish for saving/loading .bo, .mo, and .locs files.
File format is compatible with files written by deepdish so existing data still loads.

See docs/DEEPDISH_PORT_PLAN.md for full implementation plan.
"""

from __future__ import print_function, division, absolute_import
import h5py
import numpy as np
import pandas as pd

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

"""
Save/load NumPy arrays with compression
Save/load DataFrames and Series (e.g. via pandas to_hdf/read_hdf or manual column datasets)
Save/load lists of numbers
Save/load scalars and simple dicts
Walk a fixed dict structure (or a few known schemas) instead of generic recursion

Save receives a dict whose values are ndarrays, DataFrames, Series, lists, scalars, None, or nested dicts of same.
"""

def _is_scalar(val):
    if isinstance(val, (int, float, bool, str, type(None))):
        return True
    if isinstance(val, (np.integer, np.floating, np.bool_)):
        return True
    if isinstance(val, bytes):
        return True
    return False


def _write_value(grp, name, value, compression):
    """
    Write one value (array, DataFrame, Series, list, dict, or scalar) into
    group `grp` under key `name`.
    """
    # --- Scalars: store as HDF5 attributes ---
    if value is None:
        grp.attrs[name] = "__none__"  # HDF5 attrs can't store None directly
        return

    if _is_scalar(value):
        # Convert numpy scalars to Python natives for cleaner storage
        if isinstance(value, (np.integer, np.floating, np.bool_)):
            value = float(value) if isinstance(value, np.floating) else int(value) if isinstance(value, np.integer) else bool(value)
        grp.attrs[name] = value
        return

    # --- NumPy array: store as dataset with optional compression ---
    if isinstance(value, np.ndarray):
        comp = compression if compression and compression != 'default' else 'gzip'
        grp.create_dataset(name, data=value, compression=comp)
        return

    # --- Pandas DataFrame: store values + column names ---
    if isinstance(value, pd.DataFrame):
        sub = grp.create_group(name)
        sub.attrs['__pandas_type__'] = 'DataFrame'
        sub.create_dataset('values', data=value.values, compression=compression or 'gzip')
        # Store column names for reconstruction
        cols = value.columns.tolist()
        sub.attrs['columns'] = np.array(cols, dtype='S')  # fixed-length strings for HDF5
        return

    # --- Pandas Series: store values + optional name ---
    if isinstance(value, pd.Series):
        sub = grp.create_group(name)
        sub.attrs['__pandas_type__'] = 'Series'
        sub.create_dataset('values', data=value.values, compression=compression or 'gzip')
        if value.name is not None:
            sub.attrs['name'] = str(value.name)
        return

    # --- List or tuple: convert to array if numeric, else store as group ---
    if isinstance(value, (list, tuple)):
        arr = np.asarray(value)
        if arr.dtype.kind in 'iufcb':  # numeric or bool
            comp = compression if compression and compression != 'default' else 'gzip'
            grp.create_dataset(name, data=arr, compression=comp)
        else:
            sub = grp.create_group(name)
            sub.attrs['__type__'] = 'list'
            for i, v in enumerate(value):
                _write_value(sub, f'i{i}', v, compression)
            sub.attrs['__len__'] = len(value)
        return

    # --- Dict: create subgroup and recurse ---
    if isinstance(value, dict):
        sub = grp.create_group(name)
        for k, v in value.items():
            _write_value(sub, str(k), v, compression)
        return

    # --- Unsupported type (would need pickling in a full implementation) ---
    raise TypeError(f"Cannot save type {type(value)} for key '{name}'")


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

    if compression == 'default':
        compression = 'blosc'
    
    with h5py.File(path, 'w') as f:
        for key, value in data.items():
            _write_value(f, key, value, compression)


# -----------------------------------------------------------------------------
# load(path, group=None, sel=None, unpack=False)
# -----------------------------------------------------------------------------

def _read_value(node, sel=None):
    """
    Read one value from an HDF5 node (group or dataset).

    For datasets (arrays), sel applies a slice: node[sel].
    For pandas groups, sel slices the underlying 'values' dataset.
    """
    # --- Dataset: numpy array (optionally sliced) ---
    if isinstance(node, h5py.Dataset):
        if sel is not None:
            return node[sel]
        return node[()] # in hdf5, dataset[()] is the entire dataset

    # --- Group: dict, list, DataFrame, or Series ---
    if isinstance(node, h5py.Group):
        # Pandas DataFrame: group with __pandas_type__='DataFrame'
        if node.attrs.get('__pandas_type__') in (b'DataFrame', 'DataFrame'): # bytes or string
            vals = node['values']
            arr = vals[sel] if sel is not None else vals[()]
            cols = node.attrs.get('columns', [])
            cols = [c.decode() if isinstance(c, bytes) else c for c in cols]
            return pd.DataFrame(arr, columns=cols)

        # Pandas Series: group with __pandas_type__='Series'
        if node.attrs.get('__pandas_type__') in (b'Series', 'Series'):
            vals = node['values']
            arr = vals[sel] if sel is not None else vals[()]
            name = node.attrs.get('name', None)
            if isinstance(name, bytes):
                name = name.decode()
            return pd.Series(arr, name=name)

        # List stored as group (non-numeric elements): __type__='list'
        if node.attrs.get('__type__') in (b'list', 'list'):
            n = int(node.attrs['__len__'])
            out = []
            for i in range(n):
                key = f'i{i}'
                if key in node.attrs:
                    v = node.attrs[key]
                    if v == "__none__" or (isinstance(v, bytes) and v == b"__none__"):
                        out.append(None)
                    else:
                        out.append(v)
                else:
                    out.append(_read_value(node[key]))
            return out

        # Plain dict: recurse into children and attrs
        result = {}
        for key in node.keys():
            result[key] = _read_value(node[key])
        for key in node.attrs:
            if key.startswith('__'):
                continue
            v = node.attrs[key]
            if v == "__none__" or (isinstance(v, bytes) and v == b"__none__"):
                result[key] = None
            else:
                result[key] = v
        return result

    return None


def _get_node(f, group):
    """
    Navigate from root to a group, dataset, or attribute.
    Scalars (e.g. date_created) are stored as root attrs.
    """
    path = group.strip('/')           # Remove leading/trailing slashes
    if path == '':                    
        return f
    parts = path.split('/')           # Split into parts (nodes in the path)
    node = f                          # Start at root 
    for part in parts:                
        if part in node.attrs:        # 6
            v = node.attrs[part]      # 7
            if v == "__none__" or (isinstance(v, bytes) and v == b"__none__"):
                return None
            return v
        node = node[part]             # 8
    return node                       # 9


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
    with h5py.File(path, 'r') as f:
        if group is None:
            return _read_value(f,)
        
        if isinstance(group, (list, tuple)):
            out = []
            for g in group:
                n = _get_node(f, g)
                out.append(n if not isinstance(n, (h5py.Dataset, h5py.Group)) else _read_value(n, sel))
            return tuple(out) 
        
        n = _get_node(f, group)
        if not isinstance(n, (h5py.Dataset, h5py.Group)):
            return n
        return _read_value(n, sel)


__all__ = ['save', 'load', 'aslice']
