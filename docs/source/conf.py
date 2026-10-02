from importlib import metadata

project   = "walopy"
author    = "LeoSanta15"
language  = "es"
try:
    release = metadata.version("walopy")
except metadata.PackageNotFoundError:
    release = "0+unknown"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "myst_parser",
]
html_theme              = "sphinx_rtd_theme"
autodoc_member_order    = "bysource"

napoleon_use_ivar       = True
