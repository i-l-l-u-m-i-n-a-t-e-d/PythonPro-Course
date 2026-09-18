GITLAB_CI = r"""
stages:
  - build
  - test
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  key: "$CI_COMMIT_REF_SLUG"
  paths:
    - .cache/pip/

build:
  stage: build
  image: python:3.11
  script:
    - python -m pip install -r requirements.txt
    - python -m compileall -q src/

test:
  stage: test
  image: python:3.11
  script:
    - python -m pip install -r requirements.txt
    - mkdir -p reports
    - python -m pytest tests/ --junitxml=reports/junit.xml
  artifacts:
    when: always
    paths:
      - reports/junit.xml
    reports:
      junit: reports/junit.xml

deploy:
  stage: deploy
  image: alpine:3.21
  script:
    - echo "Deploying..."
"""

REQUIREMENTS_TXT = r"""
pytest
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
