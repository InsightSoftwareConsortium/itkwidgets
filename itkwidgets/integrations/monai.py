import importlib_metadata

HAVE_MONAI = False
try:
    importlib_metadata.metadata("monai")
    HAVE_MONAI = True
except importlib_metadata.PackageNotFoundError:
    pass
