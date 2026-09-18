WORKFLOW = r"""
name: Multi-job workflow

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
      - run: python -m pip install flake8
      - run: flake8 src/

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: '3.11'
      - run: python -m pip install pytest
      - run: python -m pytest tests/

  build:
    needs: [lint, test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: Zbuduj aplikację
        run: python -m compileall -q src/
"""

APP_PY = r"""
def add(a, b):
    return a + b
"""

TEST_APP_PY = r"""
from src.app import add


def test_add():
    assert add(2, 2) == 4
"""
