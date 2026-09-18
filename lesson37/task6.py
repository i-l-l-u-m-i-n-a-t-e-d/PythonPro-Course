WORKFLOW = r"""
name: Python matrix

on:
  push:

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11']
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: ${{ matrix.python-version }}
      - name: Zainstaluj pytest
        run: python -m pip install pytest
      - name: Uruchom testy
        run: python -m pytest tests
"""

TEST_MATH_PY = r"""
def test_addition():
    assert 2 + 2 == 4
"""
