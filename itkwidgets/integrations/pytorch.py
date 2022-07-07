HAVE_TORCH = False
try:
    import torch
    HAVE_TORCH = True
except ImportError:
    pass
