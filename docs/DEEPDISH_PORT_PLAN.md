# Port Off Deepdish: Implementation Plan

Replace the vendored, deprecated **deepdish** library with a thin, PyTables-based I/O layer that keeps the same file format so existing `.bo`, `.mo`, and `.locs` files keep working.

---

## 1. Scope

### 1.1 What we replace

| Current (deepdish) | New (`supereeg.io`) |
|--------------------|---------------------|
| `dd.io.save(path, obj, compression=...)` | `supereeg.io.save(path, obj, compression=...)` |
| `dd.io.load(path)` | `supereeg.io.load(path)` |
| `dd.io.load(path, group='/name')` | `supereeg.io.load(path, group='/name')` |
| `dd.io.load(path, group='/name', sel=dd.aslice[...])` | `supereeg.io.load(path, group='/name', sel=supereeg.io.aslice[...])` |
| `dd.aslice` | `supereeg.io.aslice` |

### 1.2 What we do **not** reimplement

- deepdish `image`, `util` (padding, ZCA, Saveable), `parallel`, `conf`, or the rest of `core`. SuperEEG does not use them; they can be removed after the port.

---

## 2. Data types we must support

Inferred from actual usage in `brain.py`, `model.py`, `location.py`, and `load.py`:

| Type | Used in save | Used in load |
|------|--------------|--------------|
| **dict** (string keys) | Root object for .bo, .mo, .locs | Root and `meta` |
| **numpy.ndarray** | `data`, `locs`, `numerator`, `denominator`, etc. | Same; with `sel` for partial read |
| **pandas.DataFrame** | `locs` (Model), some Brain fields | `locs`, `data` (when not sliced) |
| **pandas.Series** | `sessions`, `sample_rate` | `sessions`, `sample_rate` |
| **list** | `sample_rate`, `label`, etc. | Same |
| **scalars** (int, float, str, bool) | `n_subs`, `kurtosis_threshold`, etc. | Same |
| **None** | e.g. optional fields | Same |

We do **not** need: sparse matrices, SimpleNamespace, long lists/tuples (>255), or pickle fallback for arbitrary objects.

---

## 3. File layout compatibility

Existing files were written by deepdish with **PyTables**. Layout is:

- **Root**: HDF5 group with one child per top-level key (e.g. `data`, `locs`, `sessions`, ...).
- **Dict**: Stored as a group; title `dict:N`; children named by key.
- **List**: Stored as a group; title `list:N`; children `i0`, `i1`, ...
- **Array**: PyTables `CArray` or `Array`; optional attributes `strtype`, `itemsize`, `zeroarray_dtype`.
- **Pandas**: Stored via pandas’ own PyTables format (HDFStore); we read with `pd.read_hdf` or the same handle.
- **Scalars**: Stored as group attributes.
- **Root unpack**: Root can have attribute `DEEPDISH_IO_UNPACK` so a single-key root returns the value directly.

To stay **backward compatible**, the new layer must:

1. **Save** using the same layout (same group names, titles, and attribute names) so any existing reader still works.
2. **Load** by reading that layout (so files written by current deepdish still load).

So we implement save/load to match the existing deepdish/PyTables layout rather than inventing a new format.

---

## 4. New module layout

```
supereeg_KS/supereeg/
  io.py          # NEW: supereeg.io.save, load, aslice (thin PyTables layer)
  ...
  brain.py       # change: import supereeg.io; use io.save / io.load / io.aslice
  model.py       # same
  location.py    # same
  load.py        # same
  deepdish/      # REMOVE after port (or keep only if you need to read very old files elsewhere)
```

Optional: keep `deepdish/` in the tree temporarily and route `supereeg.io` to deepdish for one release so you can migrate gradually; then remove deepdish.

---

## 5. API specification

### 5.1 `supereeg.io.save(path, data, compression='default')`

- **path**: str, file path.
- **data**: dict with string keys only; values: ndarray, DataFrame, Series, list, tuple (length &lt; 256), scalars, None, or nested dicts of same.
- **compression**: `'default'`, `'zlib'`, `'blosc'`, `None`, or `(lib, level)` e.g. `('blosc', 5)`.
- Writes HDF5 with PyTables using the same layout as deepdish (see Section 3). Use `tables.open_file(path, 'w')`, create root group, then for each key recurse: dict → group with `_v_title = "dict:N"`, list → group `"list:N"` with `i0`, `i1`, ...; ndarray → `create_carray`/`create_array`; pandas → same as deepdish (e.g. `pd.HDFStore` with the same handle if possible, or store in a way that pandas can read back).

### 5.2 `supereeg.io.load(path, group=None, sel=None, unpack=False)`

- **path**: str.
- **group**: None (load root), str (e.g. `'/data'`, `'/locs'`), or list of strings (load multiple groups → tuple).
- **sel**: None or tuple of slice/index (e.g. from `aslice[i, j]`). Only used when loading a single group that is an array; applied as `node[sel]`.
- **unpack**: if True and root has one key, return that value instead of the dict.
- Returns: reconstructed dict/list/array/DataFrame/Series/scalar so that `Brain(**io.load(path))` and `Model(**io.load(path))` behave as today.

### 5.3 `supereeg.io.aslice`

- Same as deepdish: an object that supports `aslice[i, j]` and returns `(i, j)` so that `load(..., sel=aslice[sample_inds, loc_inds])` passes that tuple to slice the array.

Example:

```python
class SliceHelper:
    def __getitem__(self, index):
        return index
aslice = SliceHelper()
```

---

## 6. Implementation steps (order of work)

1. **Add `supereeg/io.py`**  
   - Implement `aslice` (trivial).  
   - Implement `save(path, data, compression)` for: dict, ndarray, list, tuple (len &lt; 256), scalars (as attributes), None, and pandas DataFrame/Series (using PyTables in the same way deepdish does, or `pd.DataFrame.to_hdf` under a known group name and document it).  
   - Implement `load(path, group=None, sel=None, unpack=False)`: read root or walk `group` (e.g. `/data`), handle dict/list/array/pandas/scalars/None; apply `sel` when the target is an array.

2. **Tests**  
   - Round-trip: save then load for Brain, Model, Location (or their current payload dicts).  
   - Load existing `.bo`/`.mo`/`.locs` from the repo or fixtures.  
   - Partial load: `load(path, group='/data', sel=aslice[0:10, :])` and compare to full load then slice.

3. **Switch call sites**  
   - In `brain.py`, `model.py`, `location.py`: replace `import deepdish as dd` with `from . import io` (or `from supereeg import io`); replace `dd.io.save(...)` with `io.save(...)`.  
   - In `load.py`: same; replace `dd.io.load(...)` with `io.load(...)` and `dd.aslice` with `io.aslice`.

4. **Optional: deprecate deepdish in one release**  
   - Keep `deepdish` in the tree but unused; document that I/O is now `supereeg.io`. Next release remove the `deepdish` directory.

5. **Remove deepdish**  
   - Delete `supereeg/deepdish/` and any references. Update `setup.py`/`pyproject.toml` to drop a deepdish dependency if it was ever declared.

---

## 7. Call-site summary

| File | Current | New |
|------|---------|-----|
| `brain.py` | `import deepdish as dd`; `dd.io.save(fname, bo, compression=compression)` | `from . import io`; `io.save(fname, bo, compression=compression)` |
| `model.py` | `import deepdish as dd`; `dd.io.save(fname, mo, compression=compression)` | `from . import io`; `io.save(fname, mo, compression=compression)` |
| `location.py` | `import deepdish as dd`; `dd.io.save(fname, lo, compression=compression)` | `from . import io`; `io.save(fname, lo, compression=compression)` |
| `load.py` | `import deepdish as dd`; `dd.io.load(...)`; `dd.aslice[...]` | `from . import io`; `io.load(...)`; `io.aslice[...]` |

No change to the logic of Brain/Model/Location or load(); only the import and the function names.

---

## 8. Time estimate

- **Implement `io.py` (save/load/aslice, PyTables, same layout):** 2–3 days.  
- **Tests and one-time validation on existing files:** 1 day.  
- **Call-site changes and removal of deepdish:** &lt; 1 day.  

**Total: ~1 week** for the full port with backward compatibility.

---

## 9. Skeleton and next steps

- **`supereeg/io.py`** already exists with the correct API: `save()`, `load()`, and `aslice`. The functions currently raise `NotImplementedError` with a pointer to this plan.
- **Next step:** Implement `save()` and `load()` in `io.py` following the layout in `supereeg/deepdish/io/hdf5io.py` (dict/list/array/pandas/scalars/None). Start with round-trip tests for one payload (e.g. a small Brain dict), then add group/sel and pandas.

---

## 10. References

- Current deepdish I/O: `supereeg_KS/supereeg/deepdish/io/hdf5io.py` (save/load logic and layout).  
- PyTables: https://www.pytables.org/  
- Pandas + PyTables: pandas’ `HDFStore` and `read_hdf` use PyTables under the hood; deepdish uses a custom handle (`_HDFStoreWithHandle`) to write into the same open file. Replicating that in `io.py` keeps pandas storage compatible.
