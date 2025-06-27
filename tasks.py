"""
開発中に実行したいタスクを定義しています。
"""

import webbrowser
from invoke.tasks import task
from invoke.context import Context
from pathlib import Path
import os

PACKAGES=['herms','herms-ui']

DOCS_SRC = Path("docs/source")
DOCS_OUT = Path("docs/build")
DOC_URL="http://localhost:8000/"

def _packages(name:str|None):
    if name is None:
        return PACKAGES
    else:
        return [name]

@task(optional=["package"])
def docs(c:Context,package:str|None=None, clean:bool=False):
    """Build Sphinx HTML docs.
    
    When arguments are not specified, documents for all packages are built.
    -p PACKAGE to build only the specified package.
    """
    for pkgname in _packages(package):
        srcpath=Path(pkgname) / DOCS_SRC
        destpath=Path(pkgname) / DOCS_OUT
        if clean and os.path.exists(destpath):
            c.run(f"rm -rf {destpath}")
        c.run(f"sphinx-build -b html {srcpath} {destpath}")

@task
def doc_watch(c:Context,package:str, clean:bool=False):
    """Autobuild Sphinx HTML docs.
    
    Specify a target PACKAGE. An web browser is opened to show documents for the package.
    """
    path=Path(package)
    destpath=Path(package) / DOCS_OUT
    if clean and os.path.exists(destpath):
        c.run(f"rm -rf {destpath}")
    webbrowser.open(DOC_URL)
    c.run(f"sphinx-autobuild -b html {path / DOCS_SRC} {destpath / DOCS_OUT} --watch {path / "src"}")
