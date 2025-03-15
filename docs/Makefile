# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

PYTHON        = python3

.DELETE_ON_ERROR:

all: html

prep: reference.rst description.rst guide.md guide-nb.ipynb

help:
	@sphinx-build --version
	@echo 'supported taregts: clean html dirhtml singlehtml linkcheck'

clean:
	@$(SPHINXBUILD) -M clean "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	rm -f description.rst reference.rst guide.md

html dirhtml singlehtml linkcheck: prep
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

description.rst: description.py ../README.rst
	rm -f description.rst
	$(PYTHON) description.py > description.rst
	chmod a-w description.rst

reference.rst: reference.py
	rm -f reference.rst
	$(PYTHON) reference.py > reference.rst
	chmod a-w reference.rst

guide.md: guide-proc.py guide0.md
	rm -f guide.md
	$(PYTHON) guide-proc.py > guide.md
	chmod a-w guide.md

guide-nb.ipynb: guide0.md guide-nb.py circuits-bp.jpg
	$(PYTHON) guide-nb.py > guide-nb.ipynb

circuits-bp.jpg: circuits-bp.png
	convert circuits-bp.png -interlace JPEG  -quality 65 -sampling-factor 1x1 circuits-bp.jpg

.PHONY: all prep help clean html dirhtml singlehtml linkcheck Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
#%: Makefile
#	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

