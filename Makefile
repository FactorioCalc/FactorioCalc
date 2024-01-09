all:

test: tests unittests

tests:
	python3 -m unittest discover -t . -s tests

unittests:
	python3 -m unittest discover -t . -s factoriocalc

.PHONY: all test tests unittetsts dist

dist:
	mkdir -p dist
	mkdir -p dist-bk
	if [ "`ls dist`" != "" ]; then mv dist/* dist-bk/; fi
	python3 -m build

upload:
	python3 -m twine check dist/*
	python3 -m twine upload dist/*
