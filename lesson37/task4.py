WORKFLOW = r"""
name: First test

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
      - name: Zainstaluj pytest
        run: python -m pip install pytest
      - name: Uruchom test
        run: python -m pytest tests/test_math.py
"""

TEST_MATH_PY = r"""
def test_addition():
    assert 2 + 2 == 4
"""
