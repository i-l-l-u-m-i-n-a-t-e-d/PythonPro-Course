ACTION_YML = r"""
name: Tests and coverage badge
description: Uruchamia testy i generuje badge z coverage

inputs:
  python-version:
    description: Wersja Pythona
    required: false
    default: '3.11'

runs:
  using: composite
  steps:
    - uses: actions/setup-python@v7
      with:
        python-version: ${{ inputs.python-version }}
    - shell: bash
      run: python -m pip install pytest pytest-cov
    - shell: bash
      run: python -m pytest tests/ --cov=src --cov-report=json:coverage.json
    - shell: bash
      run: python "${{ github.action_path }}/generate_badge.py" coverage.json coverage-badge.svg
"""

GENERATE_BADGE_PY = r"""
import json
import sys
from pathlib import Path


def main():
    coverage_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    data = json.loads(coverage_file.read_text(encoding="utf-8"))
    percent = round(data["totals"]["percent_covered"])
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="150" height="20" role="img" aria-label="coverage: {percent}%">\n'
        '<rect width="90" height="20" fill="#555"/><rect x="90" width="60" height="20" fill="#4c1"/>\n'
        '<text x="45" y="14" fill="#fff" text-anchor="middle" font-family="sans-serif" font-size="11">coverage</text>\n'
        f'<text x="120" y="14" fill="#fff" text-anchor="middle" font-family="sans-serif" font-size="11">{percent}%</text>\n'
        '</svg>'
    )
    output_file.write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()
"""

WORKFLOW = r"""
name: Custom coverage action

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: Uruchom własną akcję
        uses: ./.github/actions/my-action
"""
