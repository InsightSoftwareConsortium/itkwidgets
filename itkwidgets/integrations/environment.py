from enum import Enum
from importlib import import_module


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
            if 'studio-lab' in get_ipython().starting_dir:
                return  Env.SAGEMAKER
            parent_header = get_ipython().parent_header
            username = parent_header['header']['username']
            if username == '':
                return Env.JUPYTERLAB
            elif username == 'username':
                return Env.JUPYTER_NOTEBOOK
        except AttributeError:
            try:
                import js
                return Env.JUPYTERLITE
            except ImportError:
                return Env.HYPHA


ENVIRONMENT = find_env()
print(f'ENVIRONMENT: {ENVIRONMENT}')

if ENVIRONMENT is not Env.COLAB:
    if ENVIRONMENT is Env.JUPYTER_NOTEBOOK:
        try:
            import imjoy_jupyter_extension
        except:
            raise RuntimeError('imjoy-jupyter-extension is required. `pip install itkwidgets[notebook]` and refresh page.')
    else:
        try:
            import_module("imjoy-jupyterlab-extension")
        except:
            if ENVIRONMENT is Env.JUPYTERLITE:
                print('imjoy-jupyterlab-extension is required')
                raise RuntimeError('imjoy-jupyterlab-extension is required. Install the package and refresh page.')
            else:
                raise RuntimeError('imjoy-jupyterlab-extension is required. `pip install itkwidgets[lab]` and refresh page.')

try:
    import imjoy_elfinder
except:
    if ENVIRONMENT is Env.JUPYTERLITE:
        raise RuntimeError('imjoy-elfinder is required. Install the package and refresh page.')
    else:
        raise RuntimeError('imjoy-elfinder is required. `pip install imjoy-elfinder` and refresh page.')
