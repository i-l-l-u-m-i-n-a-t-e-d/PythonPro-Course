"""Monitoring, alarmy i powiadomienia dla zadania 19."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from typing import Any


NAMESPACE = "Lesson36/Application"


def ensure_log_group(logs: Any, group_name: str, retention_days: int) -> None:
    """Tworzy grupę logów aplikacji i ustawia retencję."""
    try:
        logs.create_log_group(logGroupName=group_name)
    except logs.exceptions.ResourceAlreadyExistsException:
        pass
    logs.put_retention_policy(logGroupName=group_name, retentionInDays=retention_days)


def write_application_log(logs: Any, group_name: str, stream_name: str, message: str) -> None:
    """Zapisuje pojedynczy log aplikacji do CloudWatch Logs."""
    try:
        logs.create_log_stream(logGroupName=group_name, logStreamName=stream_name)
    except logs.exceptions.ResourceAlreadyExistsException:
        pass
    logs.put_log_events(
        logGroupName=group_name,
        logStreamName=stream_name,
        logEvents=[{"timestamp": int(time.time() * 1000), "message": message}],
    )


def publish_application_metrics(
    cloudwatch: Any,
    application: str,
    request_count: float,
    error_count: float,
    latency_seconds: float,
    sample_seconds: float = 60.0,
) -> None:
    """Publikuje request rate, error rate i latency z jednego okresu pomiaru."""
    if min(request_count, error_count, latency_seconds) < 0 or sample_seconds <= 0:
        raise ValueError("Metryki nie mogą być ujemne.")
    if error_count > request_count:
        raise ValueError("Liczba błędów nie może przekraczać liczby żądań w próbce.")
    request_rate = request_count / sample_seconds
    error_rate = 0.0 if request_count == 0 else 100.0 * error_count / request_count
    dimensions = [{"Name": "Application", "Value": application}]
    timestamp = datetime.now(timezone.utc)
    cloudwatch.put_metric_data(
        Namespace=NAMESPACE,
        MetricData=[
            {
                "MetricName": "RequestRate",
                "Dimensions": dimensions,
                "Timestamp": timestamp,
                "Value": request_rate,
                "Unit": "Count/Second",
            },
            {
                "MetricName": "ErrorRate",
                "Dimensions": dimensions,
                "Timestamp": timestamp,
                "Value": error_rate,
                "Unit": "Percent",
            },
            {
                "MetricName": "Latency",
                "Dimensions": dimensions,
                "Timestamp": timestamp,
                "Value": latency_seconds,
                "Unit": "Seconds",
            },
        ],
    )


def create_topic_and_subscriptions(
    sns: Any,
    chatbot: Any,
    topic_name: str,
    email: str,
    chatbot_role_arn: str,
    slack_team_id: str,
    slack_channel_id: str,
) -> str:
    """Łączy SNS z e-mailem oraz skonfigurowanym kanałem Slack."""
    topic_arn = sns.create_topic(Name=topic_name)["TopicArn"]
    email_exists = False
    paginator = sns.get_paginator("list_subscriptions_by_topic")
    for page in paginator.paginate(TopicArn=topic_arn):
        email_exists = email_exists or any(
            subscription.get("Protocol") == "email"
            and subscription.get("Endpoint", "").lower() == email.lower()
            for subscription in page.get("Subscriptions", [])
        )
    if not email_exists:
        sns.subscribe(TopicArn=topic_arn, Protocol="email", Endpoint=email)

    configuration_name = f"{topic_name}-slack"
    existing: dict[str, Any] | None = None
    next_token: str | None = None
    while True:
        request = {"MaxResults": 50}
        if next_token:
            request["NextToken"] = next_token
        page = chatbot.describe_slack_channel_configurations(**request)
        existing = next(
            (
                item
                for item in page.get("SlackChannelConfigurations", [])
                if item.get("ConfigurationName") == configuration_name
            ),
            None,
        )
        if existing or not page.get("NextToken"):
            break
        next_token = page["NextToken"]
    if existing:
        if existing.get("SlackTeamId") != slack_team_id:
            raise ValueError("Istniejąca konfiguracja Slack dotyczy innego Slack Team.")
        chatbot.update_slack_channel_configuration(
            ChatConfigurationArn=existing["ChatConfigurationArn"],
            IamRoleArn=chatbot_role_arn,
            SlackChannelId=slack_channel_id,
            SnsTopicArns=[topic_arn],
            LoggingLevel="ERROR",
        )
    else:
        chatbot.create_slack_channel_configuration(
            ConfigurationName=configuration_name,
            IamRoleArn=chatbot_role_arn,
            SlackTeamId=slack_team_id,
            SlackChannelId=slack_channel_id,
            SnsTopicArns=[topic_arn],
            LoggingLevel="ERROR",
        )
    return topic_arn


def create_alarms(
    cloudwatch: Any, application: str, asg_name: str, topic_arn: str
) -> None:
    """Tworzy alarmy CPU, błędów procentowych i opóźnienia."""
    app_dimensions = [{"Name": "Application", "Value": application}]
    cloudwatch.put_metric_alarm(
        AlarmName=f"{application}-cpu-over-80",
        AlarmDescription="CPU przekracza 80% przez pięć minut.",
        Namespace="AWS/EC2",
        MetricName="CPUUtilization",
        Dimensions=[{"Name": "AutoScalingGroupName", "Value": asg_name}],
        Statistic="Average",
        Period=300,
        EvaluationPeriods=1,
        Threshold=80.0,
        ComparisonOperator="GreaterThanThreshold",
        TreatMissingData="notBreaching",
        AlarmActions=[topic_arn],
    )
    cloudwatch.put_metric_alarm(
        AlarmName=f"{application}-error-rate-over-5",
        AlarmDescription="Error rate przekracza 5%.",
        Namespace=NAMESPACE,
        MetricName="ErrorRate",
        Dimensions=app_dimensions,
        Statistic="Average",
        Period=60,
        ComparisonOperator="GreaterThanThreshold",
        Threshold=5.0,
        EvaluationPeriods=1,
        TreatMissingData="notBreaching",
        AlarmActions=[topic_arn],
    )
    cloudwatch.put_metric_alarm(
        AlarmName=f"{application}-latency-over-2-seconds",
        AlarmDescription="Średnie opóźnienie przekracza dwie sekundy.",
        Namespace=NAMESPACE,
        MetricName="Latency",
        Dimensions=app_dimensions,
        Statistic="Average",
        Period=60,
        EvaluationPeriods=1,
        Threshold=2.0,
        ComparisonOperator="GreaterThanThreshold",
        TreatMissingData="notBreaching",
        AlarmActions=[topic_arn],
    )


def create_dashboard(cloudwatch: Any, application: str, asg_name: str) -> None:
    """Tworzy dashboard z najważniejszymi metrykami aplikacji."""
    app_dimensions = ["Application", application]
    dashboard = {
        "widgets": [
            {
                "type": "metric",
                "x": 0,
                "y": 0,
                "width": 12,
                "height": 6,
                "properties": {
                    "title": "CPU Auto Scaling Group",
                    "view": "timeSeries",
                    "metrics": [
                        ["AWS/EC2", "CPUUtilization", "AutoScalingGroupName", asg_name]
                    ],
                    "stat": "Average",
                    "period": 300,
                },
            },
            {
                "type": "metric",
                "x": 12,
                "y": 0,
                "width": 12,
                "height": 6,
                "properties": {
                    "title": "Request rate, error rate i latency",
                    "view": "timeSeries",
                    "metrics": [
                        [NAMESPACE, "RequestRate", *app_dimensions, {"stat": "Average"}],
                        [".", "ErrorRate", ".", ".", {"stat": "Average"}],
                        [".", "Latency", ".", ".", {"stat": "Average"}],
                    ],
                    "period": 60,
                },
            },
        ]
    }
    cloudwatch.put_dashboard(
        DashboardName=f"{application}-monitoring", DashboardBody=json.dumps(dashboard)
    )


def require_confirmation(value: str | None) -> None:
    if value != "MONITORING":
        raise SystemExit("Podaj --confirm MONITORING, aby utworzyć zasoby AWS.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Konfiguruje monitoring aplikacji.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm")
    parser.add_argument("--region", default="eu-central-1")
    parser.add_argument("--application", required=True)
    parser.add_argument("--asg-name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--chatbot-role-arn", required=True)
    parser.add_argument("--slack-team-id", required=True)
    parser.add_argument("--slack-channel-id", required=True)
    parser.add_argument("--log-group")
    parser.add_argument("--log-stream", default="application")
    parser.add_argument("--log-message", default="Monitoring configured")
    parser.add_argument("--retention-days", type=int, default=30)
    parser.add_argument("--request-count", type=float, default=0)
    parser.add_argument("--error-count", type=float, default=0)
    parser.add_argument("--latency-seconds", type=float, default=0)
    parser.add_argument("--sample-seconds", type=float, default=60.0)
    args = parser.parse_args()

    if not args.apply:
        raise SystemExit("To polecenie wymaga jawnej opcji --apply.")
    if args.retention_days < 1 or args.sample_seconds <= 0:
        raise SystemExit("Retencja i czas próbki muszą być dodatnie.")
    require_confirmation(args.confirm)

    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError

        session = boto3.Session(region_name=args.region)
        cloudwatch = session.client("cloudwatch")
        logs = session.client("logs")
        sns = session.client("sns")
        chatbot = session.client("chatbot")
        log_group = args.log_group or f"/lesson36/{args.application}"
        ensure_log_group(logs, log_group, args.retention_days)
        write_application_log(logs, log_group, args.log_stream, args.log_message)
        publish_application_metrics(
            cloudwatch,
            args.application,
            args.request_count,
            args.error_count,
            args.latency_seconds,
            args.sample_seconds,
        )
        topic_arn = create_topic_and_subscriptions(
            sns,
            chatbot,
            f"{args.application}-alerts",
            args.email,
            args.chatbot_role_arn,
            args.slack_team_id,
            args.slack_channel_id,
        )
        create_alarms(cloudwatch, args.application, args.asg_name, topic_arn)
        create_dashboard(cloudwatch, args.application, args.asg_name)
    except (BotoCoreError, ClientError) as error:
        raise SystemExit(f"Operacja AWS nie powiodła się: {error}") from error

    print("Monitoring został skonfigurowany.")


if __name__ == "__main__":
    main()
