"""Infrastructure as Code boto3 dla pełnej infrastruktury produkcyjnej."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class InfrastructureConfig:
    app_name: str
    region: str
    availability_zones: list[str]
    hosted_zone_id: str
    domain_name: str
    certificate_arn: str
    image_id: str
    bucket_name: str
    db_instance_class: str
    master_username: str
    master_password: str


def safe_name(value: str) -> str:
    name = re.sub(r"[^a-z0-9-]", "-", value.lower()).strip("-")
    if not name:
        raise ValueError("Nazwa aplikacji nie może być pusta.")
    return name[:20]


def tag_spec(resource_type: str, name: str) -> list[dict[str, Any]]:
    return [{"ResourceType": resource_type, "Tags": [{"Key": "Name", "Value": name}]}]


def create_network(ec2: Any, config: InfrastructureConfig) -> dict[str, Any]:
    """Tworzy VPC oraz trzy publiczne i trzy prywatne subnety."""
    if len(set(config.availability_zones)) != 3:
        raise ValueError("Podaj dokładnie trzy różne Availability Zones.")
    app = config.app_name
    vpc = ec2.create_vpc(
        CidrBlock="10.36.0.0/16", TagSpecifications=tag_spec("vpc", f"{app}-vpc")
    )["Vpc"]
    vpc_id = vpc["VpcId"]
    ec2.get_waiter("vpc_available").wait(VpcIds=[vpc_id])
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={"Value": True})
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={"Value": True})

    igw_id = ec2.create_internet_gateway(
        TagSpecifications=tag_spec("internet-gateway", f"{app}-igw")
    )["InternetGateway"]["InternetGatewayId"]
    ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
    public_routes = ec2.create_route_table(
        VpcId=vpc_id, TagSpecifications=tag_spec("route-table", f"{app}-public-rt")
    )["RouteTable"]["RouteTableId"]
    private_routes = ec2.create_route_table(
        VpcId=vpc_id, TagSpecifications=tag_spec("route-table", f"{app}-private-rt")
    )["RouteTable"]["RouteTableId"]
    ec2.create_route(
        RouteTableId=public_routes,
        DestinationCidrBlock="0.0.0.0/0",
        GatewayId=igw_id,
    )

    public_subnets: list[str] = []
    private_subnets: list[str] = []
    for index, zone in enumerate(config.availability_zones):
        public_id = ec2.create_subnet(
            VpcId=vpc_id,
            CidrBlock=f"10.36.{index}.0/24",
            AvailabilityZone=zone,
            TagSpecifications=tag_spec("subnet", f"{app}-public-{index + 1}"),
        )["Subnet"]["SubnetId"]
        private_id = ec2.create_subnet(
            VpcId=vpc_id,
            CidrBlock=f"10.36.{index + 16}.0/24",
            AvailabilityZone=zone,
            TagSpecifications=tag_spec("subnet", f"{app}-private-{index + 1}"),
        )["Subnet"]["SubnetId"]
        ec2.modify_subnet_attribute(SubnetId=public_id, MapPublicIpOnLaunch={"Value": True})
        ec2.associate_route_table(SubnetId=public_id, RouteTableId=public_routes)
        ec2.associate_route_table(SubnetId=private_id, RouteTableId=private_routes)
        public_subnets.append(public_id)
        private_subnets.append(private_id)
    ec2.create_vpc_endpoint(
        VpcEndpointType="Gateway",
        VpcId=vpc_id,
        ServiceName=f"com.amazonaws.{config.region}.s3",
        RouteTableIds=[private_routes],
    )
    return {
        "vpc_id": vpc_id,
        "public_subnets": public_subnets,
        "private_subnets": private_subnets,
        "private_route_table": private_routes,
    }


def create_security_groups(ec2: Any, vpc_id: str, app: str) -> dict[str, str]:
    """Stosuje zasadę least privilege między ALB, EC2 i RDS."""
    alb_sg = ec2.create_security_group(
        GroupName=f"{app}-alb-sg", Description="HTTPS only for ALB", VpcId=vpc_id
    )["GroupId"]
    app_sg = ec2.create_security_group(
        GroupName=f"{app}-app-sg", Description="Application from ALB", VpcId=vpc_id
    )["GroupId"]
    rds_sg = ec2.create_security_group(
        GroupName=f"{app}-rds-sg", Description="PostgreSQL from application", VpcId=vpc_id
    )["GroupId"]
    ec2.authorize_security_group_ingress(
        GroupId=alb_sg,
        IpPermissions=[
            {
                "IpProtocol": "tcp",
                "FromPort": 80,
                "ToPort": 80,
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            },
            {
                "IpProtocol": "tcp",
                "FromPort": 443,
                "ToPort": 443,
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            },
        ],
    )
    ec2.authorize_security_group_ingress(
        GroupId=app_sg,
        IpPermissions=[
            {
                "IpProtocol": "tcp",
                "FromPort": 8000,
                "ToPort": 8000,
                "UserIdGroupPairs": [{"GroupId": alb_sg}],
            }
        ],
    )
    ec2.authorize_security_group_ingress(
        GroupId=rds_sg,
        IpPermissions=[
            {
                "IpProtocol": "tcp",
                "FromPort": 5432,
                "ToPort": 5432,
                "UserIdGroupPairs": [{"GroupId": app_sg}],
            }
        ],
    )
    return {"alb": alb_sg, "app": app_sg, "rds": rds_sg}


def create_secrets_manager_endpoint(
    ec2: Any, config: InfrastructureConfig, vpc_id: str, private_subnets: list[str], app_sg: str
) -> None:
    """Udostępnia Secrets Manager prywatnym instancjom bez publicznego Internetu."""
    endpoint_sg = ec2.create_security_group(
        GroupName=f"{config.app_name}-secrets-endpoint-sg",
        Description="HTTPS from application instances to Secrets Manager",
        VpcId=vpc_id,
    )["GroupId"]
    ec2.authorize_security_group_ingress(
        GroupId=endpoint_sg,
        IpPermissions=[
            {
                "IpProtocol": "tcp",
                "FromPort": 443,
                "ToPort": 443,
                "UserIdGroupPairs": [{"GroupId": app_sg}],
            }
        ],
    )
    ec2.create_vpc_endpoint(
        VpcEndpointType="Interface",
        VpcId=vpc_id,
        ServiceName=f"com.amazonaws.{config.region}.secretsmanager",
        SubnetIds=private_subnets,
        SecurityGroupIds=[endpoint_sg],
        PrivateDnsEnabled=True,
    )


def create_release_bucket(s3: Any, config: InfrastructureConfig) -> None:
    """Włącza versioning oraz archiwizację starszych wydań."""
    if config.region == "us-east-1":
        s3.create_bucket(Bucket=config.bucket_name)
    else:
        s3.create_bucket(
            Bucket=config.bucket_name,
            CreateBucketConfiguration={"LocationConstraint": config.region},
        )
    s3.put_bucket_versioning(
        Bucket=config.bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    s3.put_public_access_block(
        Bucket=config.bucket_name,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
    s3.put_bucket_lifecycle_configuration(
        Bucket=config.bucket_name,
        LifecycleConfiguration={
            "Rules": [
                {
                    "ID": "archive-old-releases",
                    "Status": "Enabled",
                    "Filter": {"Prefix": "releases/"},
                    "NoncurrentVersionTransitions": [
                        {"NoncurrentDays": 30, "StorageClass": "GLACIER"}
                    ],
                }
            ]
        },
    )


def create_database_secret(secrets: Any, config: InfrastructureConfig) -> str:
    """Zapisuje poświadczenia RDS w Secrets Manager, nie w kodzie."""
    response = secrets.create_secret(
        Name=f"{config.app_name}/rds/master",
        Description="Credentials for the production RDS instance",
        SecretString=json.dumps(
            {"username": config.master_username, "password": config.master_password}
        ),
    )
    return response["ARN"]


def create_database(
    rds: Any,
    config: InfrastructureConfig,
    private_subnets: list[str],
    rds_security_group: str,
) -> tuple[str, str, list[str]]:
    """Tworzy Multi-AZ PostgreSQL i dwie Read Replicas."""
    subnet_group = f"{config.app_name}-db-subnets"
    rds.create_db_subnet_group(
        DBSubnetGroupName=subnet_group,
        DBSubnetGroupDescription="Private subnets for production RDS",
        SubnetIds=private_subnets,
        Tags=[{"Key": "Name", "Value": subnet_group}],
    )
    primary_id = f"{config.app_name}-primary"
    rds.create_db_instance(
        DBInstanceIdentifier=primary_id,
        DBInstanceClass=config.db_instance_class,
        Engine="postgres",
        MasterUsername=config.master_username,
        MasterUserPassword=config.master_password,
        AllocatedStorage=20,
        StorageType="gp3",
        StorageEncrypted=True,
        MultiAZ=True,
        PubliclyAccessible=False,
        BackupRetentionPeriod=7,
        CopyTagsToSnapshot=True,
        DBSubnetGroupName=subnet_group,
        VpcSecurityGroupIds=[rds_security_group],
        Tags=[{"Key": "Name", "Value": primary_id}],
    )
    waiter = rds.get_waiter("db_instance_available")
    waiter.wait(DBInstanceIdentifier=primary_id)
    primary = rds.describe_db_instances(DBInstanceIdentifier=primary_id)["DBInstances"][0]
    endpoint = primary["Endpoint"]["Address"]
    replica_ids: list[str] = []
    for number in (1, 2):
        replica_id = f"{config.app_name}-replica-{number}"
        rds.create_db_instance_read_replica(
            DBInstanceIdentifier=replica_id,
            SourceDBInstanceIdentifier=primary_id,
            DBInstanceClass=config.db_instance_class,
            PubliclyAccessible=False,
            Tags=[{"Key": "Name", "Value": replica_id}],
        )
        waiter.wait(DBInstanceIdentifier=replica_id)
        replica_ids.append(replica_id)
    return primary_id, endpoint, replica_ids


def create_instance_profile(
    iam: Any, config: InfrastructureConfig, secret_arn: str
) -> str:
    """Tworzy rolę EC2 z minimalnym dostępem do releasów i sekretu."""
    role_name = f"{config.app_name}-ec2-role"
    assume_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "ec2.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(assume_policy),
        Description="Least-privilege role for the production application",
    )
    resource_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject"],
                "Resource": f"arn:aws:s3:::{config.bucket_name}/releases/*",
            },
            {
                "Effect": "Allow",
                "Action": ["secretsmanager:GetSecretValue"],
                "Resource": secret_arn,
            },
        ],
    }
    iam.put_role_policy(
        RoleName=role_name,
        PolicyName=f"{config.app_name}-read-runtime-config",
        PolicyDocument=json.dumps(resource_policy),
    )
    profile_name = f"{config.app_name}-ec2-profile"
    iam.create_instance_profile(InstanceProfileName=profile_name)
    iam.add_role_to_instance_profile(InstanceProfileName=profile_name, RoleName=role_name)
    return profile_name


def user_data(bucket: str, release_key: str, endpoint: str, secret_arn: str) -> str:
    """Buduje user data pobierające wydanie bez ujawniania hasła bazy."""
    script = f"""#!/bin/bash
set -euo pipefail
mkdir -p /opt/app
aws s3 cp s3://{bucket}/{release_key} /opt/app/release.zip
unzip -o /opt/app/release.zip -d /opt/app
cat > /opt/app/runtime.env <<'EOF'
DATABASE_HOST={endpoint}
DATABASE_SECRET_ARN={secret_arn}
APP_PORT=8000
EOF
chmod 600 /opt/app/runtime.env
cd /opt/app
./start.sh
"""
    return base64.b64encode(script.encode("utf-8")).decode("ascii")


def create_launch_template(
    ec2: Any,
    config: InfrastructureConfig,
    deployment: str,
    app_security_group: str,
    profile_name: str,
    endpoint: str,
    secret_arn: str,
) -> str:
    """Tworzy Launch Template z osobnym artefaktem stable albo canary."""
    template_name = f"{config.app_name}-{deployment}-template"
    template = ec2.create_launch_template(
        LaunchTemplateName=template_name,
        LaunchTemplateData={
            "ImageId": config.image_id,
            "InstanceType": "t3.micro",
            "SecurityGroupIds": [app_security_group],
            "IamInstanceProfile": {"Name": profile_name},
            "UserData": user_data(
                config.bucket_name,
                f"releases/{deployment}.zip",
                endpoint,
                secret_arn,
            ),
            "Monitoring": {"Enabled": True},
            "TagSpecifications": [
                {
                    "ResourceType": "instance",
                    "Tags": [
                        {"Key": "Name", "Value": f"{config.app_name}-{deployment}"},
                        {"Key": "Deployment", "Value": deployment},
                    ],
                }
            ],
        },
    )["LaunchTemplate"]
    return template["LaunchTemplateId"]


def create_alb_stack(
    elbv2: Any,
    config: InfrastructureConfig,
    deployment: str,
    vpc_id: str,
    public_subnets: list[str],
    alb_security_group: str,
) -> dict[str, str]:
    """Tworzy ALB SSL, Target Group i przekierowanie HTTP na HTTPS."""
    target_group = elbv2.create_target_group(
        Name=f"{config.app_name}-{deployment}-tg",
        Protocol="HTTP",
        Port=8000,
        VpcId=vpc_id,
        TargetType="instance",
        HealthCheckEnabled=True,
        HealthCheckProtocol="HTTP",
        HealthCheckPath="/health",
        HealthCheckIntervalSeconds=30,
        HealthCheckTimeoutSeconds=5,
        HealthyThresholdCount=2,
        UnhealthyThresholdCount=3,
    )["TargetGroups"][0]
    load_balancer = elbv2.create_load_balancer(
        Name=f"{config.app_name}-{deployment}-alb",
        Subnets=public_subnets,
        SecurityGroups=[alb_security_group],
        Scheme="internet-facing",
        Type="application",
        IpAddressType="ipv4",
        Tags=[
            {"Key": "Name", "Value": f"{config.app_name}-{deployment}-alb"},
            {"Key": "Deployment", "Value": deployment},
        ],
    )["LoadBalancers"][0]
    alb_arn = load_balancer["LoadBalancerArn"]
    elbv2.get_waiter("load_balancer_available").wait(LoadBalancerArns=[alb_arn])
    elbv2.create_listener(
        LoadBalancerArn=alb_arn,
        Protocol="HTTPS",
        Port=443,
        Certificates=[{"CertificateArn": config.certificate_arn}],
        DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group["TargetGroupArn"]}],
    )
    elbv2.create_listener(
        LoadBalancerArn=alb_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[
            {
                "Type": "redirect",
                "RedirectConfig": {
                    "Protocol": "HTTPS",
                    "Port": "443",
                    "Host": "#{host}",
                    "Path": "/#{path}",
                    "Query": "#{query}",
                    "StatusCode": "HTTP_301",
                },
            }
        ],
    )
    return {
        "alb_arn": alb_arn,
        "dns_name": load_balancer["DNSName"],
        "hosted_zone_id": load_balancer["CanonicalHostedZoneId"],
        "target_group_arn": target_group["TargetGroupArn"],
    }


def create_auto_scaling_group(
    autoscaling: Any,
    config: InfrastructureConfig,
    deployment: str,
    template_id: str,
    private_subnets: list[str],
    target_group_arn: str,
) -> str:
    """Tworzy stabilną grupę 2–20 oraz mniejszą grupę canary."""
    is_stable = deployment == "stable"
    group_name = f"{config.app_name}-{deployment}-asg"
    autoscaling.create_auto_scaling_group(
        AutoScalingGroupName=group_name,
        LaunchTemplate={"LaunchTemplateId": template_id, "Version": "$Latest"},
        MinSize=2 if is_stable else 1,
        MaxSize=20 if is_stable else 2,
        DesiredCapacity=2 if is_stable else 1,
        VPCZoneIdentifier=",".join(private_subnets),
        TargetGroupARNs=[target_group_arn],
        HealthCheckType="ELB",
        HealthCheckGracePeriod=300,
        Tags=[
            {
                "Key": "Name",
                "Value": group_name,
                "PropagateAtLaunch": True,
            },
            {
                "Key": "Deployment",
                "Value": deployment,
                "PropagateAtLaunch": True,
            },
        ],
    )
    return group_name


def wait_for_healthy_asg_targets(
    autoscaling: Any,
    elbv2: Any,
    asg_name: str,
    target_group_arn: str,
    required_capacity: int,
    timeout_seconds: int = 900,
) -> None:
    """Nie dopuszcza DNS do momentu, gdy ALB potwierdzi zdrowe targety."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        groups = autoscaling.describe_auto_scaling_groups(
            AutoScalingGroupNames=[asg_name]
        ).get("AutoScalingGroups", [])
        if not groups:
            raise RuntimeError(f"Nie znaleziono Auto Scaling Group {asg_name}.")
        instance_ids = [
            item["InstanceId"]
            for item in groups[0].get("Instances", [])
            if item.get("LifecycleState") == "InService"
        ]
        if len(instance_ids) >= required_capacity:
            health = elbv2.describe_target_health(TargetGroupArn=target_group_arn)
            states = {
                item.get("Target", {}).get("Id"): item.get("TargetHealth", {}).get("State")
                for item in health.get("TargetHealthDescriptions", [])
            }
            if all(states.get(instance_id) == "healthy" for instance_id in instance_ids):
                return
        time.sleep(15)
    raise TimeoutError(f"Targety ASG {asg_name} nie osiągnęły stanu healthy.")


def validate_hosted_zone(route53: Any, config: InfrastructureConfig) -> str:
    """Sprawdza, czy rekord 90/10 należy do podanej Hosted Zone."""
    hosted_zone_id = config.hosted_zone_id.rsplit("/", 1)[-1]
    zone_name = route53.get_hosted_zone(Id=hosted_zone_id)["HostedZone"]["Name"].rstrip(".").lower()
    record_name = config.domain_name.rstrip(".").lower()
    if record_name != zone_name and not record_name.endswith(f".{zone_name}"):
        raise ValueError("Nazwa domeny nie należy do wskazanej Hosted Zone.")
    return hosted_zone_id


def create_weighted_dns(
    route53: Any,
    config: InfrastructureConfig,
    stable: dict[str, str],
    canary: dict[str, str],
) -> None:
    """Konfiguruje Route53: 90% stable, 10% canary."""
    hosted_zone_id = validate_hosted_zone(route53, config)
    response = route53.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            "Comment": "90 percent stable, 10 percent canary",
            "Changes": [
                {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": config.domain_name,
                        "Type": "A",
                        "SetIdentifier": "stable",
                        "Weight": 90,
                        "AliasTarget": {
                            "HostedZoneId": stable["hosted_zone_id"],
                            "DNSName": stable["dns_name"],
                            "EvaluateTargetHealth": True,
                        },
                    },
                },
                {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": config.domain_name,
                        "Type": "A",
                        "SetIdentifier": "canary",
                        "Weight": 10,
                        "AliasTarget": {
                            "HostedZoneId": canary["hosted_zone_id"],
                            "DNSName": canary["dns_name"],
                            "EvaluateTargetHealth": True,
                        },
                    },
                },
            ],
        },
    )
    route53.get_waiter("resource_record_sets_changed").wait(
        Id=response["ChangeInfo"]["Id"]
    )


def create_monitoring(
    cloudwatch: Any, config: InfrastructureConfig, stable: dict[str, str]
) -> None:
    """Tworzy alarm zdrowia ALB i dashboard produkcyjny."""
    target_dimension = stable["target_group_arn"].split(":", maxsplit=5)[-1]
    alb_dimension = stable["alb_arn"].split(":", maxsplit=5)[-1]
    cloudwatch.put_metric_alarm(
        AlarmName=f"{config.app_name}-unhealthy-targets",
        AlarmDescription="Co najmniej jeden target ALB jest unhealthy.",
        Namespace="AWS/ApplicationELB",
        MetricName="UnHealthyHostCount",
        Dimensions=[
            {"Name": "TargetGroup", "Value": target_dimension},
            {"Name": "LoadBalancer", "Value": alb_dimension},
        ],
        Statistic="Maximum",
        Period=60,
        EvaluationPeriods=1,
        Threshold=1,
        ComparisonOperator="GreaterThanOrEqualToThreshold",
        TreatMissingData="notBreaching",
    )
    dashboard = {
        "widgets": [
            {
                "type": "metric",
                "x": 0,
                "y": 0,
                "width": 12,
                "height": 6,
                "properties": {
                    "title": "ALB requests and unhealthy targets",
                    "view": "timeSeries",
                    "metrics": [
                        [
                            "AWS/ApplicationELB",
                            "RequestCount",
                            "LoadBalancer",
                            alb_dimension,
                            {"stat": "Sum"},
                        ],
                        [
                            ".",
                            "UnHealthyHostCount",
                            "TargetGroup",
                            target_dimension,
                            "LoadBalancer",
                            alb_dimension,
                            {"stat": "Maximum"},
                        ],
                    ],
                    "period": 60,
                },
            }
        ]
    }
    cloudwatch.put_dashboard(
        DashboardName=f"{config.app_name}-production", DashboardBody=json.dumps(dashboard)
    )


def create_and_attach_waf(wafv2: Any, config: InfrastructureConfig, alb_arns: list[str]) -> None:
    """Tworzy regionalny Web ACL z zarządzaną regułą AWS."""
    response = wafv2.create_web_acl(
        Name=f"{config.app_name}-web-acl",
        Scope="REGIONAL",
        DefaultAction={"Allow": {}},
        Description="Managed baseline protection for the production ALBs",
        VisibilityConfig={
            "SampledRequestsEnabled": True,
            "CloudWatchMetricsEnabled": True,
            "MetricName": f"{config.app_name}WebAcl",
        },
        Rules=[
            {
                "Name": "AWSManagedCommonRules",
                "Priority": 1,
                "OverrideAction": {"None": {}},
                "Statement": {
                    "ManagedRuleGroupStatement": {
                        "VendorName": "AWS",
                        "Name": "AWSManagedRulesCommonRuleSet",
                    }
                },
                "VisibilityConfig": {
                    "SampledRequestsEnabled": True,
                    "CloudWatchMetricsEnabled": True,
                    "MetricName": "AWSManagedCommonRules",
                },
            }
        ],
    )
    web_acl_arn = response["Summary"]["ARN"]
    for attempt in range(6):
        try:
            for alb_arn in alb_arns:
                wafv2.associate_web_acl(WebACLArn=web_acl_arn, ResourceArn=alb_arn)
            return
        except wafv2.exceptions.WAFUnavailableEntityException:
            if attempt == 5:
                raise
            time.sleep(5)


CI_CD_WORKFLOW = """name: Production deployment
on:
  push:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: read
  id-token: write
env:
  AWS_REGION: __AWS_REGION__
  RELEASE_BUCKET: __RELEASE_BUCKET__
  STAGING_ASG: __CANARY_ASG__
  STABLE_ASG: __STABLE_ASG__
  APP_HEALTH_URL: https://__DOMAIN_NAME__/health
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: '3.13'
      - run: pip install -r requirements.txt pytest
      - run: pytest tests/unit tests/integration
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
      - name: Package and deploy staging
        run: |
          zip -r release.zip . -x '.git/*' '.github/*' 'tests/*' '__pycache__/*'
          aws s3 cp release.zip "s3://$RELEASE_BUCKET/releases/canary.zip"
          template_id=$(aws autoscaling describe-auto-scaling-groups \
            --auto-scaling-group-names "$STAGING_ASG" \
            --query 'AutoScalingGroups[0].LaunchTemplate.LaunchTemplateId' --output text)
          version=$(aws ec2 create-launch-template-version \
            --launch-template-id "$template_id" --source-version '$Latest' \
            --query 'LaunchTemplateVersion.VersionNumber' --output text)
          aws autoscaling start-instance-refresh --auto-scaling-group-name "$STAGING_ASG" \
            --desired-configuration "LaunchTemplate={LaunchTemplateId=$template_id,Version=$version}" \
            --preferences 'MinHealthyPercentage=50,AutoRollback=true'
          aws autoscaling wait instance-refresh-complete --auto-scaling-group-name "$STAGING_ASG"
  production:
    needs: staging
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v6
      - uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}
      - name: Package and deploy stable release
        run: |
          zip -r release.zip . -x '.git/*' '.github/*' 'tests/*' '__pycache__/*'
          aws s3 cp release.zip "s3://$RELEASE_BUCKET/releases/stable.zip"
          template_id=$(aws autoscaling describe-auto-scaling-groups \
            --auto-scaling-group-names "$STABLE_ASG" \
            --query 'AutoScalingGroups[0].LaunchTemplate.LaunchTemplateId' --output text)
          version=$(aws ec2 create-launch-template-version \
            --launch-template-id "$template_id" --source-version '$Latest' \
            --query 'LaunchTemplateVersion.VersionNumber' --output text)
          aws autoscaling start-instance-refresh --auto-scaling-group-name "$STABLE_ASG" \
            --desired-configuration "LaunchTemplate={LaunchTemplateId=$template_id,Version=$version}" \
            --preferences 'MinHealthyPercentage=50,InstanceWarmup=180,AutoRollback=true'
          aws autoscaling wait instance-refresh-complete --auto-scaling-group-name "$STABLE_ASG"
          curl --fail --retry 12 --retry-delay 10 "$APP_HEALTH_URL"
"""


def write_workflow(path: Path, config: InfrastructureConfig) -> None:
    """Zapisuje workflow GitHub Actions dopiero podczas provisioningu."""
    path.parent.mkdir(parents=True, exist_ok=True)
    workflow = (
        CI_CD_WORKFLOW.replace("__AWS_REGION__", config.region)
        .replace("__RELEASE_BUCKET__", config.bucket_name)
        .replace("__CANARY_ASG__", f"{config.app_name}-canary-asg")
        .replace("__STABLE_ASG__", f"{config.app_name}-stable-asg")
        .replace("__DOMAIN_NAME__", config.domain_name.rstrip("."))
    )
    path.write_text(workflow, encoding="utf-8")


def provision(config: InfrastructureConfig, workflow_path: Path) -> None:
    """Wykonuje kolejno wszystkie zależne elementy infrastruktury."""
    import boto3

    session = boto3.Session(region_name=config.region)
    ec2 = session.client("ec2")
    rds = session.client("rds")
    s3 = session.client("s3")
    secrets = session.client("secretsmanager")
    iam = session.client("iam")
    elbv2 = session.client("elbv2")
    autoscaling = session.client("autoscaling")
    route53 = session.client("route53")
    cloudwatch = session.client("cloudwatch")
    wafv2 = session.client("wafv2")

    network = create_network(ec2, config)
    security_groups = create_security_groups(ec2, network["vpc_id"], config.app_name)
    create_secrets_manager_endpoint(
        ec2,
        config,
        network["vpc_id"],
        network["private_subnets"],
        security_groups["app"],
    )
    create_release_bucket(s3, config)
    secret_arn = create_database_secret(secrets, config)
    _, db_endpoint, _ = create_database(
        rds, config, network["private_subnets"], security_groups["rds"]
    )
    profile_name = create_instance_profile(iam, config, secret_arn)

    stable_template = create_launch_template(
        ec2,
        config,
        "stable",
        security_groups["app"],
        profile_name,
        db_endpoint,
        secret_arn,
    )
    canary_template = create_launch_template(
        ec2,
        config,
        "canary",
        security_groups["app"],
        profile_name,
        db_endpoint,
        secret_arn,
    )
    stable = create_alb_stack(
        elbv2,
        config,
        "stable",
        network["vpc_id"],
        network["public_subnets"],
        security_groups["alb"],
    )
    canary = create_alb_stack(
        elbv2,
        config,
        "canary",
        network["vpc_id"],
        network["public_subnets"],
        security_groups["alb"],
    )
    stable_asg = create_auto_scaling_group(
        autoscaling,
        config,
        "stable",
        stable_template,
        network["private_subnets"],
        stable["target_group_arn"],
    )
    canary_asg = create_auto_scaling_group(
        autoscaling,
        config,
        "canary",
        canary_template,
        network["private_subnets"],
        canary["target_group_arn"],
    )
    wait_for_healthy_asg_targets(
        autoscaling, elbv2, stable_asg, stable["target_group_arn"], required_capacity=2
    )
    wait_for_healthy_asg_targets(
        autoscaling, elbv2, canary_asg, canary["target_group_arn"], required_capacity=1
    )
    create_weighted_dns(route53, config, stable, canary)
    create_monitoring(cloudwatch, config, stable)
    create_and_attach_waf(wafv2, config, [stable["alb_arn"], canary["alb_arn"]])
    write_workflow(workflow_path, config)


def main() -> None:
    parser = argparse.ArgumentParser(description="Buduje pełną infrastrukturę produkcyjną.")
    parser.add_argument("--apply", action="store_true", help="Tworzy zasoby AWS.")
    parser.add_argument("--confirm", help="Musi być równe nazwie aplikacji.")
    parser.add_argument("--app-name", required=True)
    parser.add_argument("--region", default="eu-central-1")
    parser.add_argument("--availability-zones", nargs=3, required=True)
    parser.add_argument("--hosted-zone-id", required=True)
    parser.add_argument("--domain-name", required=True)
    parser.add_argument("--certificate-arn", required=True)
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--bucket-name", required=True)
    parser.add_argument("--db-instance-class", default="db.t3.micro")
    parser.add_argument("--master-username", default="dbadmin")
    parser.add_argument("--master-password-env", default="RDS_MASTER_PASSWORD")
    parser.add_argument(
        "--workflow-output",
        type=Path,
        default=Path(".github/workflows/deploy.yml"),
    )
    args = parser.parse_args()

    app_name = safe_name(args.app_name)
    if not args.apply:
        raise SystemExit("Provisioning wymaga jawnej opcji --apply.")
    if args.confirm != app_name:
        raise SystemExit("Podaj --confirm z bezpieczną nazwą aplikacji.")
    master_password = os.environ.get(args.master_password_env)
    if not master_password:
        raise SystemExit(
            f"Brakuje hasła bazy w zmiennej środowiskowej {args.master_password_env}."
        )
    config = InfrastructureConfig(
        app_name=app_name,
        region=args.region,
        availability_zones=args.availability_zones,
        hosted_zone_id=args.hosted_zone_id,
        domain_name=args.domain_name.rstrip(".") + ".",
        certificate_arn=args.certificate_arn,
        image_id=args.image_id,
        bucket_name=args.bucket_name,
        db_instance_class=args.db_instance_class,
        master_username=args.master_username,
        master_password=master_password,
    )
    try:
        from botocore.exceptions import BotoCoreError, ClientError

        provision(config, args.workflow_output)
    except (BotoCoreError, ClientError) as error:
        raise SystemExit(f"Provisioning AWS nie powiodło się: {error}") from error

    print("Infrastructure provisioning started successfully.")


if __name__ == "__main__":
    main()
