WORKFLOW = r"""
name: Full CI/CD pipeline

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
      - run: python -m pip install flake8 black
      - run: flake8 src/ tests/
      - run: black --check src/ tests/

  test:
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: '3.11'
      - run: python -m pip install pytest pytest-cov
      - run: python -m pytest tests/ --cov=src

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: Build Docker image
        run: docker build -t lesson38-app:${{ github.sha }} .

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying..."
"""

APP_PY = r"""
def add(a, b):
    return a + b


if __name__ == "__main__":
    print(add(2, 2))
"""

TEST_APP_PY = r"""
from src.app import add


def test_add():
    assert add(2, 2) == 4
"""

DOCKERFILE = r"""
FROM python:3.11-slim
WORKDIR /app
COPY src/ ./src/
CMD ["python", "-m", "src.app"]
"""
