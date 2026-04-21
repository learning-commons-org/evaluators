VENV	  := ../.venv
PIP	      := $(VENV)/bin/pip
PYTHON	  := $(VENV)/bin/python
JUPYTER	  := $(VENV)/bin/jupyter
CONFIGS	  := .env

$(VENV):
	python3 -m venv $(VENV)

$(PIP): $(VENV)
	$(PYTHON) -m pip install --upgrade pip

$(JUPYTER): $(PIP)

jupyter: $(JUPYTER)
	$(JUPYTER) lab

install: $(VENV) $(PIP)
	$(PIP) install -r requirements.txt
	$(foreach x,$(CONFIGS),cp -n $(x).example $(x); ) true

.PHONY: install jupyter
