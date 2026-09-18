WORKFLOW = r"""
name: Pip cache

on:
  push:

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: '3.11'
      - name: Cache pip
        uses: actions/cache@v6
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-
      - name: Zainstaluj zależności
        run: python -m pip install -r requirements.txt
"""

REQUIREMENTS_TXT = r"""
pytest
"""
