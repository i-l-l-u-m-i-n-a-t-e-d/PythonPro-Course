WORKFLOW = r"""
name: Workflow triggers

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Workflow started"
"""
