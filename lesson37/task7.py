WORKFLOW = r"""
name: Flake8

on:
  push:

permissions:
  contents: read

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: '3.11'
      - name: Zainstaluj flake8
        run: python -m pip install flake8
      - name: Uruchom flake8
        run: flake8 src/
"""

APP_PY = r"""
def hello():
    return "Hello, CI/CD!"
"""
