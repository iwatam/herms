project = 'herms'
copyright = '2025, iwatam'
author = 'iwatam'
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
    "myst_parser",
]

templates_path = ['_templates']
exclude_patterns = []

language = 'ja'
html_theme = 'alabaster'
html_static_path = ['_static']

import os
import sys
sys.path.insert(0, os.path.abspath("../../src"))
