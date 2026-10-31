.PHONY: install test scan monitor sense clean

VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
PYTEST = $(VENV)/bin/pytest

install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e .
	$(PIP) install pytest

test:
	$(PYTEST) tests/ -v

scan:
	$(PYTHON) -m prober.cli scan --duration 10

monitor:
	$(PYTHON) -m prober.cli monitor

sense:
	$(PYTHON) -m prober.cli sense

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache
