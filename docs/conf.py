# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))
from pathlib import Path
from sphinx.application import Sphinx
import subprocess
import os
import re
from datetime import date

# -- Project information -----------------------------------------------------

project = 'itkwidgets'
author = 'Matthew McCormick'
copyright = f'{date.today().year}, NumFOCUS'
author = 'Insight Software Consortium'

# The full version, including alpha/beta/rc tags.
release = re.sub('^v', '', os.popen('git tag --list "v1.0*" --sort=creatordate').readlines()[-1].strip())
# The short X.Y version.
version = release


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autosummary',
    'autodoc2',
    'myst_parser',
    'sphinx_copybutton',
    'sphinx.ext.intersphinx',
    'sphinxext.opengraph',
    'sphinx_design',
]

autodoc2_packages = [
    {
        "path": "../itkwidgets",
        "exclude_files": [],
    },
]
autodoc2_render_plugin = "myst"

myst_enable_extensions = [
    "colon_fence",
    "dollarmath",  # Support syntax for inline and block math using `$...$` and `$$...$$`
                   # (see https://myst-parser.readthedocs.io/en/latest/syntax/optional.html#dollar-delimited-math)
    "fieldlist",
    "linkify",  # convert bare links to hyperlinks
]

intersphinx_mapping = {
    "itkwasm": ("https://wasm.itk.org/en/latest/", None),
    "python": ("https://docs.python.org/3/", None),
    "numpy": ("https://numpy.org/doc/stable", None),
}

html_theme_options = dict(
    github_url='https://github.com/InsightSoftwareConsortium/itkwidgets',
    icon_links=[],
)

# jupyterlite_config = jupyterlite_dir / "jupyterlite_config.json"

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'furo'
html_logo = "_static/itkwidgets_logo_small.png"
html_favicon = "_static/favicon/favicon.ico"
html_title = f"{project}'s documentation"

# Furo options
html_theme_options = {
    "top_of_page_button": "edit",
    "source_repository": "https://github.com/InsightSoftwareConsortium/itkwidgets/",
    "source_branch": "main",
    "source_directory": "docs",
}


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static',
        'jupyterlite/_output']

def jupyterlite_build(app: Sphinx, error):
    here = Path(__file__).parent.resolve()
    jupyterlite_config = here / "jupyterlite" / "jupyterlite_config.json"
    subprocess.check_call(['jupyter', 'lite', 'build', '--config',
        str(jupyterlite_config)], cwd=str(here / 'jupyterlite'))

def setup(app):
    # For local builds, you can run jupyter lite build manually
    # $ cd jupyterlite
    # $ jupyter lite serve --config ./jupyterlite_config.json
    app.connect("config-inited", jupyterlite_build)
