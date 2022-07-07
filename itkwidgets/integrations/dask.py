HAVE_DASK = False
try:
    import dask.array
    HAVE_DASK = True
except ImportError:
    pass

import numpy as np


def dask_array_to_ndarray(dask_array):
    array = np.asarray(dask_array)
    array = np.ascontiguousarray(array)
    # JavaScript does not support 64-bit integers
    if array.dtype == np.int64:
        array = array.astype(np.float32)
    elif array.dtype == np.uint64:
        array = array.astype(np.float32)
    return array
