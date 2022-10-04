HAVE_XARRAY = False
try:
    import xarray
    HAVE_XARRAY = True
except ImportError:
    pass

HAVE_MULTISCALE_SPATIAL_IMAGE = False
try:
    import multiscale_spatial_image
    HAVE_MULTISCALE_SPATIAL_IMAGE = True
except ImportError:
    pass

def xarray_data_array_to_numpy(data_array):
    return data_array.to_numpy()

def xarray_data_set_to_numpy(data_set):
    return xarray_data_array_to_numpy(data_set.to_array(name='Dataset'))
