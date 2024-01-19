# Development

## Package

Setup your system for development:

```bash
git clone https://github.com/InsightSoftwareConsortium/itkwidgets.git
cd itkwidgets
pip install -e ".[test,lab,notebook,cli]"
pytest
pytest --nbmake examples/*.ipynb
```

If Python code is changed, restart the kernel to see the changes.

**Warning**: This project is under active development. Its API and behavior may change at any time. We mean it 🙃.

## Documentation

Setup your system for documentation development on Unix-like systems:

```bash
git clone https://github.com/InsightSoftwareConsortium/itkwidgets.git
cd itkwidgets/docs
pip install -r requirements.txt
```

Build and serve the documentation:

```bash
make html
python -m http.server -d _build/html 8787
```

Then visit *http://localhost:8787/* to see the rendered documentation.

### JupyterLite

The documentation includes an embedded JupyterLite deployment. To update the
JupyterLite deployment, it is recommended to call `make clean` before starting
a new build to avoid build caching issues. Also, serve the rendered
documentation on a different port to avoid browser caching issues.

Notebooks served in the JupyterLite deployment can be found at
*docs/jupyterlite/files*.

Support package wheels, including the `itkwidgets` wheel are referenced in
*docs/jupyter/jupyterlite_config.json*. To update the URLs there, copy the
download link address for a wheel found at https://pypi.org in a package's *Download
files* page. Additional wheel files, if not on PyPI, can be added directly at
*docs/jupyterlite/files/*.
