from enum import Enum
from importlib import import_module
import sys


class Env(Enum):
    JUPYTER_NOTEBOOK = 'notebook'
    JUPYTERLAB = 'lab'
    JUPYTERLITE = 'lite'
    SAGEMAKER = 'sagemaker'
    HYPHA = 'hypha'
    COLAB = 'colab'


def find_env():
    try:
        from google.colab import files
        return Env.COLAB
    except:
        try:
            from IPython import get_ipython
            parent_header = get_ipython().parent_header
            username = parent_header['header']['username']
            if username == '':
                return Env.JUPYTERLAB
            elif username == 'username':
                return Env.JUPYTER_NOTEBOOK
            else:
                return Env.SAGEMAKER
        except AttributeError:
            try:
                import js
                return Env.JUPYTERLITE
            except ImportError:
                return Env.HYPHA


ENVIRONMENT = find_env()

if ENVIRONMENT is not Env.JUPYTERLITE:
    if ENVIRONMENT is not Env.COLAB:
        if ENVIRONMENT is Env.JUPYTER_NOTEBOOK and sys.version_info.minor > 7:
            try:
                import imjoy_jupyter_extension
            except:
                raise RuntimeError('imjoy-jupyter-extension is required. `pip install itkwidgets[notebook]` and refresh page.')
        else:
            try:
                import_module("imjoy-jupyterlab-extension")
            except:
                if ENVIRONMENT is Env.JUPYTERLITE:
                    raise RuntimeError('imjoy-jupyterlab-extension is required. Install the package and refresh page.')
                elif sys.version_info.minor > 7:
                    raise RuntimeError('imjoy-jupyterlab-extension is required. `pip install itkwidgets[lab]` and refresh page.')

    try:
        import imjoy_elfinder
    except:
        if ENVIRONMENT is Env.JUPYTERLITE:
            raise RuntimeError('imjoy-elfinder is required. Install the package and refresh page.')
        elif sys.version_info.minor > 7:
            raise RuntimeError('imjoy-elfinder is required. `pip install imjoy-elfinder` and refresh page.')
