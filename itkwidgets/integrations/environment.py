from enum import Enum
from importlib import import_module
from packaging import version
import importlib_metadata
import sys


class Env(Enum):
    JUPYTER = 'jupyter'
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
                return Env.JUPYTER
            else:
                return Env.SAGEMAKER
        except:
            if sys.platform == 'emscripten':
                return Env.JUPYTERLITE
            return Env.HYPHA


ENVIRONMENT = find_env()

if ENVIRONMENT is not Env.JUPYTERLITE and ENVIRONMENT is not Env.HYPHA:
    if ENVIRONMENT is not Env.COLAB:
        if ENVIRONMENT is Env.JUPYTER:
            try:
                notebook_version = importlib_metadata.version('notebook')
                if version.parse(notebook_version) < version.parse('7'):
                    raise RuntimeError('itkwidgets 1.0a51 and newer requires Jupyter notebook>=7.')
            except importlib_metadata.PackageNotFoundError:
                # notebook may not be available
                pass
            try:
                lab_version = importlib_metadata.version('jupyterlab')
                if version.parse(lab_version) < version.parse('4'):
                    raise RuntimeError('itkwidgets 1.0a51 and newer requires jupyterlab>=4.')
            except importlib_metadata.PackageNotFoundError:
                # jupyterlab may not be available
                pass
        try:
            import_module("imjoy-jupyterlab-extension")
        except ModuleNotFoundError:
            try:
                import_module("imjoy_jupyterlab_extension")
            except ModuleNotFoundError:
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
