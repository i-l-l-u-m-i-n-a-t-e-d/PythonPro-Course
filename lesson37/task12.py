WORKFLOW = r"""
name: Conditional step

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
      - run: python -m pip install pytest
      - name: Testy
        run: python -m pytest tests/
      - name: Gotowe do wdrożenia
        if: ${{ success() && github.ref == 'refs/heads/main' }}
        run: echo "Ready to deploy!"
"""

TEST_MATH_PY = r"""
def test_addition():
    assert 2 + 2 == 4
"""
