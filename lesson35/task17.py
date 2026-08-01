"""Generator workflow CI/CD dla zadania 17."""

from __future__ import annotations

import argparse
from pathlib import Path


WORKFLOW = r"""name: CI/CD to AWS

on:
  push:
  workflow_dispatch:
    inputs:
      production_approval:
        description: 'Wybierz APPROVE-PRODUCTION, aby po staging uruchomić produkcję.'
        required: true
        type: choice
        default: 'DO-NOT-DEPLOY'
        options:
          - DO-NOT-DEPLOY
          - APPROVE-PRODUCTION

permissions:
  contents: read
  id-token: write

env:
  AWS_REGION: ${{ vars.AWS_REGION }}
  STAGING_ASG: ${{ vars.STAGING_ASG }}
  PRODUCTION_ASG: ${{ vars.PRODUCTION_ASG }}
  RELEASE_BUCKET: ${{ vars.RELEASE_BUCKET }}
  STAGING_HEALTH_URL: ${{ vars.STAGING_HEALTH_URL }}
  PRODUCTION_HEALTH_URL: ${{ vars.PRODUCTION_HEALTH_URL }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest
      - name: Unit and integration tests
        run: pytest tests/unit tests/integration

  staging:
    needs: test
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v6
      - uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}
      - name: Package and upload release
        run: |
          zip -r release.zip . -x '.git/*' '.github/*' '__pycache__/*' 'tests/*'
          aws s3 cp release.zip "s3://$RELEASE_BUCKET/staging/release.zip"
      - name: Rolling staging deployment with rollback
        run: |
          template_id=$(aws autoscaling describe-auto-scaling-groups \
            --auto-scaling-group-names "$STAGING_ASG" \
            --query 'AutoScalingGroups[0].LaunchTemplate.LaunchTemplateId' --output text)
          version=$(aws ec2 create-launch-template-version \
            --launch-template-id "$template_id" --source-version '$Latest' \
            --query 'LaunchTemplateVersion.VersionNumber' --output text)
          aws autoscaling start-instance-refresh --auto-scaling-group-name "$STAGING_ASG" \
            --desired-configuration "LaunchTemplate={LaunchTemplateId=$template_id,Version=$version}" \
            --preferences 'MinHealthyPercentage=50,InstanceWarmup=120,AutoRollback=true'
          aws autoscaling wait instance-refresh-complete --auto-scaling-group-name "$STAGING_ASG"
      - name: Verify staging health
        run: curl --fail --retry 12 --retry-delay 10 "$STAGING_HEALTH_URL/health"

  production:
    needs: staging
    if: ${{ github.event_name == 'workflow_dispatch' && inputs.production_approval == 'APPROVE-PRODUCTION' }}
    runs-on: ubuntu-latest
    environment:
      name: production
    outputs:
      template_id: ${{ steps.current.outputs.template_id }}
      previous_version: ${{ steps.current.outputs.previous_version }}
    steps:
      - uses: actions/checkout@v6
      - uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}
      - name: Upload production release
        run: |
          zip -r release.zip . -x '.git/*' '.github/*' '__pycache__/*' 'tests/*'
          aws s3 cp release.zip "s3://$RELEASE_BUCKET/production/release.zip"
          aws s3 cp release.zip "s3://$RELEASE_BUCKET/releases/latest.zip"
      - name: Remember current launch template
        id: current
        run: |
          template_id=$(aws autoscaling describe-auto-scaling-groups \
            --auto-scaling-group-names "$PRODUCTION_ASG" \
            --query 'AutoScalingGroups[0].LaunchTemplate.LaunchTemplateId' --output text)
          previous_version=$(aws autoscaling describe-auto-scaling-groups \
            --auto-scaling-group-names "$PRODUCTION_ASG" \
            --query 'AutoScalingGroups[0].LaunchTemplate.Version' --output text)
          test "$template_id" != "None"
          test "$previous_version" != "None"
          echo "template_id=$template_id" >> "$GITHUB_OUTPUT"
          echo "previous_version=$previous_version" >> "$GITHUB_OUTPUT"
      - name: Zero-downtime production refresh
        run: |
          template_id=$(aws autoscaling describe-auto-scaling-groups \
            --auto-scaling-group-names "$PRODUCTION_ASG" \
            --query 'AutoScalingGroups[0].LaunchTemplate.LaunchTemplateId' --output text)
          version=$(aws ec2 create-launch-template-version \
            --launch-template-id "$template_id" --source-version '$Latest' \
            --query 'LaunchTemplateVersion.VersionNumber' --output text)
          aws autoscaling start-instance-refresh --auto-scaling-group-name "$PRODUCTION_ASG" \
            --desired-configuration "LaunchTemplate={LaunchTemplateId=$template_id,Version=$version}" \
            --preferences 'MinHealthyPercentage=50,InstanceWarmup=180,AutoRollback=true'
          aws autoscaling wait instance-refresh-complete --auto-scaling-group-name "$PRODUCTION_ASG"
      - name: Verify production health
        run: curl --fail --retry 12 --retry-delay 10 "$PRODUCTION_HEALTH_URL/health"

  rollback:
    needs: production
    if: ${{ always() && needs.production.result == 'failure' && needs.production.outputs.template_id != '' }}
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}
      - name: Restore previous launch template version
        run: |
          aws autoscaling update-auto-scaling-group \
            --auto-scaling-group-name "$PRODUCTION_ASG" \
            --launch-template "LaunchTemplateId=${{ needs.production.outputs.template_id }},Version=${{ needs.production.outputs.previous_version }}"
          aws autoscaling start-instance-refresh \
            --auto-scaling-group-name "$PRODUCTION_ASG" \
            --desired-configuration "LaunchTemplate={LaunchTemplateId=${{ needs.production.outputs.template_id }},Version=${{ needs.production.outputs.previous_version }}}" \
            --preferences 'MinHealthyPercentage=50,InstanceWarmup=180'
          aws autoscaling wait instance-refresh-complete \
            --auto-scaling-group-name "$PRODUCTION_ASG"
      - name: Confirm recovered service
        run: curl --fail --retry 12 --retry-delay 10 "$PRODUCTION_HEALTH_URL/health"

  notify:
    needs: [test, staging, production, rollback]
    if: ${{ always() }}
    runs-on: ubuntu-latest
    steps:
      - name: Notify Slack
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
        run: |
          payload=$(printf '{"text":"CI/CD: test=%s staging=%s production=%s rollback=%s"}' \
            '${{ needs.test.result }}' '${{ needs.staging.result }}' \
            '${{ needs.production.result }}' '${{ needs.rollback.result }}')
          curl --fail --show-error --silent -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-Type: application/json' --data "$payload"
"""


def write_workflow(output_path: Path) -> None:
    """Zapisuje gotowy workflow, bez zapisywania sekretów."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(WORKFLOW, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generuje workflow GitHub Actions.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".github/workflows/deploy.yml"),
        help="Docelowa ścieżka YAML.",
    )
    args = parser.parse_args()
    write_workflow(args.output)
    print(f"Utworzono workflow: {args.output}")


if __name__ == "__main__":
    main()
