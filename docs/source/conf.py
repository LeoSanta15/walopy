import walopy

project   = "walopy"
author    = "LeoSanta15"
language  = "es"
release   = walopy.__version__
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "myst_parser",
]
html_theme              = "sphinx_rtd_theme"
autodoc_member_order    = "bysource"

napoleon_use_ivar       = True
