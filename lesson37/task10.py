WORKFLOW = r"""
name: Test artifact

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
      - name: Uruchom testy i zapisz raport
        run: |
          mkdir -p reports
          python -m pytest tests/ --junitxml=reports/junit.xml
      - name: Zapisz wyniki testów
        if: always()
        uses: actions/upload-artifact@v7
        with:
          name: test-results
          path: reports/junit.xml
          if-no-files-found: error
"""

TEST_MATH_PY = r"""
def test_addition():
    assert 2 + 2 == 4
"""
