WORKFLOW = r"""
name: Install dependencies

on:
  push:

permissions:
  contents: read

jobs:
  dependencies:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: '3.11'
      - name: Zainstaluj zależności
        run: python -m pip install -r requirements.txt
"""

REQUIREMENTS_TXT = r"""
requests
pytest
"""
