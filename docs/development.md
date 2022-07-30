# Development

Note: [Node.js](https://nodejs.org/en/download/) is required for development.

Setup your system for development:

```bash
git clone https://github.com/InsightSoftwareConsortium/itkwidgets.git
cd itkwidgets

Choose your target platform.  If you are developing for jupyter notebooks:
```bash
pip install -e .[notebook]

If you are developing for jupyter labs:
```bash
pip install -e .[lab]

Then verify your installation:
pytest
pytest --nbmake examples/*.ipynb
```

If Python code is changed, restart the kernel to see the changes.

**Warning**: This project is under active development. Its API and behavior may change at any time. We mean it.
