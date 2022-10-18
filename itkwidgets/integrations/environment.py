IN_JUPYTER_NOTEBOOK = False
IN_JUPYTERLAB = False
IN_JUPYTERLITE = False
IN_AWS = False

try:
    from google.colab import files
    IN_COLAB = True
except:
    IN_COLAB = False

if not IN_COLAB:
    try:
        from IPython import get_ipython
        parent_header = get_ipython().parent_header
        username = parent_header['header']['username']
        if username == '':
            IN_JUPYTERLAB = True
        elif username == 'username':
            IN_JUPYTER_NOTEBOOK = True
        else:
            IN_AWS = True
    except AttributeError:
        IN_JUPYTERLITE = True
