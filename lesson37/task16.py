WORKFLOW = r"""
name: Secrets management

on:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    env:
      API_KEY: ${{ secrets.API_KEY }}
    steps:
      - name: Pokaż maskowaną wartość
        run: |
          test -n "$API_KEY"
          echo "::add-mask::$API_KEY"
          echo "API_KEY=$API_KEY"
      - name: Symuluj deploy
        run: echo "Deploying with API key..."
"""
