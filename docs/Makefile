SPHINXBUILD ?= sphinx-build

.PHONY: html doctest clean
html:
	$(SPHINXBUILD) -W --keep-going -b html source build/html
doctest:
	$(SPHINXBUILD) -W --keep-going -b doctest source build/doctest
clean:
	rm -rf build source/gallery
