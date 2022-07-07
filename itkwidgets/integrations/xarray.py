HAVE_XARRAY = False
try:
    import xarray
    HAVE_XARRAY = True
except ImportError:
    pass

def xarray_data_array_to_numpy(data_array):
    return data_array.to_numpy()

def xarray_data_set_to_numpy(data_set):
    return xarray_data_array_to_numpy(data_set.to_array(name='Dataset'))
