WORKFLOW = r"""
name: Environment variables

on:
  push:

env:
  APP_NAME: lesson38

permissions:
  contents: read

jobs:
  show-env:
    runs-on: ubuntu-latest
    env:
      ENVIRONMENT: test
    steps:
      - name: Wyświetl zmienne
        run: |
          echo "APP_NAME=$APP_NAME"
          echo "ENVIRONMENT=$ENVIRONMENT"
"""
