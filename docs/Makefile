# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

PYTHON        = python3

all: html

help:
	@sphinx-build --version
	@echo 'supported taregts: clean html dirhtml singlehtml linkcheck'

clean:
	rm reference.rst
	@$(SPHINXBUILD) -M clean "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

html dirhtml singlehtml linkcheck: reference.rst description.rst
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

description.rst: description.py ../README.rst
	$(PYTHON) description.py > description.rst

reference.rst: reference.py
	$(PYTHON) reference.py > reference.rst

.PHONY: all help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
#%: Makefile
#	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

