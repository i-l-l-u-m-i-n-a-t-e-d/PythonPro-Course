WORKFLOW = r"""
name: Hello CI/CD

on:
  push:

permissions:
  contents: read

jobs:
  hello:
    runs-on: ubuntu-latest
    steps:
      - name: Powitanie
        run: echo "Hello, CI/CD!"
"""
