WORKFLOW = r"""
name: Scheduled security scan

on:
  schedule:
    - cron: '0 3 * * *'

permissions:
  contents: read
  issues: write

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: '3.11'
      - name: Zainstaluj pip-audit
        run: python -m pip install pip-audit
      - name: Security scan
        id: audit
        shell: bash
        run: |
          set +e
          pip-audit -r requirements.txt --format=json --output=pip-audit.json
          status=$?
          set -e
          case "$status" in
            0) echo "vulnerabilities=false" >> "$GITHUB_OUTPUT" ;;
            1) echo "vulnerabilities=true" >> "$GITHUB_OUTPUT" ;;
            *) exit "$status" ;;
          esac
      - name: Utwórz Issue dla wykrytych podatności
        if: ${{ steps.audit.outputs.vulnerabilities == 'true' }}
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh issue create --title "pip-audit: wykryto podatności" --body-file pip-audit.json
"""

REQUIREMENTS_TXT = r"""
requests
"""
