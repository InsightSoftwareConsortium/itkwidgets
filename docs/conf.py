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

# -- Project information -----------------------------------------------------

project = 'itkwidgets'
copyright = '2022, Matthew McCormick'
author = 'Matthew McCormick'

# The full version, including alpha/beta/rc tags.
release = re.sub('^v', '', os.popen('git describe').read().strip())
# The short X.Y version.
version = release


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['myst_parser',]

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
html_theme = 'pydata_sphinx_theme'

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
