from enum import Enum


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
