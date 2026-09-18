PY ?= python3

.PHONY: test validate check

test:
	$(PY) -m unittest discover -s tests -t .

validate:
	$(PY) -m sdlc validate

# Everything CI runs before a PR can merge.
check: test validate
