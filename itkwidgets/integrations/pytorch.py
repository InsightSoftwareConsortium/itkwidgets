import importlib_metadata

HAVE_TORCH = False
try:
    importlib_metadata.metadata("torch")
    HAVE_TORCH = True
except importlib_metadata.PackageNotFoundError:
    pass
