import importlib_metadata

HAVE_XARRAY = False
try:
    importlib_metadata.metadata("xarray")
    HAVE_XARRAY = True
except importlib_metadata.PackageNotFoundError:
    pass

HAVE_MULTISCALE_SPATIAL_IMAGE = False
try:
    importlib_metadata.metadata("multiscale-spatial-image")
    HAVE_MULTISCALE_SPATIAL_IMAGE = True
except importlib_metadata.PackageNotFoundError:
    pass

def xarray_data_array_to_numpy(data_array):
    return data_array.to_numpy()

def xarray_data_set_to_numpy(data_set):
    return xarray_data_array_to_numpy(data_set.to_array(name='Dataset'))
