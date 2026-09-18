WORKFLOW = r"""
name: Python workflow

on:
  push:

permissions:
  contents: read

jobs:
  run-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@v7
        with:
          python-version: '3.11'
      - name: Utwórz plik Python
        run: |
          cat > hello.py <<'PY'
          def hello():
              print("Hello from Python!")


          if __name__ == "__main__":
              hello()
          PY
      - name: Uruchom program
        run: python hello.py
"""
