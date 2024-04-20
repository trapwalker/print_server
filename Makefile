APP_NAME=print_server
ENTRY_POINT=print_server/__main__.py
VENV_NAME=venv
VENV_PATH=./$(VENV_NAME)/bin

venv:
	python -m venv $(VENV_NAME)

install_deps:
	$(VENV_NAME)/bin/pip install -e .

install_deps_dev: install_deps
	$(VENV_NAME)/bin/pip install -r dev-requirements.txt

build:
	$(VENV_PATH)/pyinstaller --onefile --name $(APP_NAME) $(ENTRY_POINT)

clean:
	rm -rf build dist $(APP_NAME).spec

.PHONY: build clean
