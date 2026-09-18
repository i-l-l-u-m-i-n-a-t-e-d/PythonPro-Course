WORKFLOW = r"""
name: Multi-platform testing

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.9', '3.10', '3.11']
        exclude:
          - os: windows-latest
            python-version: '3.9'
        include:
          - os: windows-latest
            python-version: '3.9'
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: ${{ matrix.python-version }}
      - run: python -m pip install pytest
      - run: python -m pytest tests/
"""

TEST_MATH_PY = r"""
def test_addition():
    assert 2 + 2 == 4
"""
