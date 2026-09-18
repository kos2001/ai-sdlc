PY ?= python3

.PHONY: test validate lessons check

test:
	$(PY) -m unittest discover -s tests -t .

validate:
	$(PY) -m sdlc validate

# A closed lesson whose control has disappeared fails the build.
lessons:
	$(PY) -m sdlc lessons check

# Everything CI runs before a PR can merge.
check: test validate lessons
