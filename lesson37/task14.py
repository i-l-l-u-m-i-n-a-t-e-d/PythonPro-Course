WORKFLOW = r"""
name: Docker to GHCR

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  packages: write

jobs:
  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: Ustal nazwę obrazu
        id: image
        run: echo "name=ghcr.io/${GITHUB_REPOSITORY,,}" >> "$GITHUB_OUTPUT"
      - uses: docker/setup-buildx-action@v4
      - name: Zbuduj obraz
        uses: docker/build-push-action@v7
        with:
          context: .
          load: true
          push: false
          tags: ${{ steps.image.outputs.name }}:${{ github.sha }}
      - name: Uruchom testy w kontenerze
        run: docker run --rm "${{ steps.image.outputs.name }}:${GITHUB_SHA}" python -m pytest tests/
      - name: Zaloguj do GHCR
        uses: docker/login-action@v4
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Push do GHCR
        run: docker push "${{ steps.image.outputs.name }}:${GITHUB_SHA}"
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

DOCKERFILE = r"""
FROM python:3.11-slim
WORKDIR /app
RUN python -m pip install --no-cache-dir pytest
COPY src/ ./src/
COPY tests/ ./tests/
CMD ["python", "-m", "pytest", "tests/"]
"""
