WORKFLOW = r"""
name: Deploy to AWS ECS

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  AWS_REGION: eu-west-1
  ECR_REPOSITORY: lesson38-app
  ECS_CLUSTER: lesson38-cluster
  ECS_SERVICE: lesson38-service

permissions:
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: Skonfiguruj AWS credentials
        uses: aws-actions/configure-aws-credentials@v6
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      - name: Zaloguj do ECR
        id: ecr
        uses: aws-actions/amazon-ecr-login@v2
      - name: Zbuduj obraz
        env:
          REGISTRY: ${{ steps.ecr.outputs.registry }}
        run: docker build -t "$REGISTRY/$ECR_REPOSITORY:latest" .
      - name: Push do ECR
        env:
          REGISTRY: ${{ steps.ecr.outputs.registry }}
        run: docker push "$REGISTRY/$ECR_REPOSITORY:latest"
      - name: Update ECS service
        run: aws ecs update-service --cluster "$ECS_CLUSTER" --service "$ECS_SERVICE" --force-new-deployment
"""

APP_PY = r"""
print("Hello from AWS deployment")
"""

DOCKERFILE = r"""
FROM python:3.11-slim
WORKDIR /app
COPY src/ ./src/
CMD ["python", "src/app.py"]
"""
