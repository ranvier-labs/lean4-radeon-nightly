.PHONY: check test validate build
check: test validate
	bash -n scripts/publish.sh

test:
	python3 -m unittest discover -s tests -v

validate:
	python3 scripts/release.py validate releases

build: validate
	python3 scripts/build_index.py
