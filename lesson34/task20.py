import argparse
from pathlib import Path


MONTH_HOURS = 24 * 30
LOW_CPU_PERCENT = 20
RESERVED_DISCOUNT = 0.30
HOURLY_PRICES = {"t3.micro": 0.01, "t3.small": 0.02, "t3.medium": 0.04}
FAKE_INSTANCES = [
    {
        "id": "i-demo-001",
        "state": "running",
        "instance_type": "t3.micro",
        "running_hours": MONTH_HOURS,
        "average_cpu": 8,
        "attached_volumes": [],
    },
    {
        "id": "i-demo-002",
        "state": "stopped",
        "instance_type": "t3.small",
        "running_hours": 0,
        "average_cpu": 0,
        "attached_volumes": [{"id": "vol-demo-001", "monthly_cost": 4.5}],
    },
]


def _number(value: object, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Nieprawidłowa wartość pola {field}.") from error
    if result < 0:
        raise ValueError(f"Pole {field} nie może być ujemne.")
    return result


def analyze_costs(
    instances: list[dict],
    period_hours: int = MONTH_HOURS,
    low_cpu_percent: int = LOW_CPU_PERCENT,
) -> dict:
    if period_hours <= 0 or low_cpu_percent < 0:
        raise ValueError("Parametry analizy muszą być dodatnie.")

    reserved_candidates = []
    wasted_volumes = []
    for instance in instances:
        instance_id = instance.get("id")
        state = instance.get("state")
        instance_type = instance.get("instance_type")
        if not instance_id or not state or not instance_type:
            raise ValueError("Każda instancja musi mieć id, stan i typ.")

        running_hours = _number(instance.get("running_hours"), "running_hours")
        average_cpu = _number(instance.get("average_cpu"), "average_cpu")
        if (
            state == "running"
            and running_hours >= period_hours
            and average_cpu < low_cpu_percent
            and instance_type in HOURLY_PRICES
        ):
            monthly_cost = HOURLY_PRICES[instance_type] * period_hours
            reserved_candidates.append(
                {
                    "instance_id": instance_id,
                    "monthly_cost": monthly_cost,
                    "estimated_savings": monthly_cost * RESERVED_DISCOUNT,
                }
            )

        if state == "stopped":
            for volume in instance.get("attached_volumes", []):
                volume_cost = _number(volume.get("monthly_cost"), "monthly_cost")
                wasted_volumes.append(
                    {
                        "instance_id": instance_id,
                        "volume_id": volume.get("id", "nieznany"),
                        "monthly_cost": volume_cost,
                    }
                )

    total_savings = sum(
        item["estimated_savings"] for item in reserved_candidates
    ) + sum(item["monthly_cost"] for item in wasted_volumes)
    return {
        "reserved_candidates": reserved_candidates,
        "wasted_volumes": wasted_volumes,
        "estimated_monthly_savings": total_savings,
    }


def generate_report(analysis: dict, output_file: str | Path) -> Path:
    lines = ["# Rekomendacje optymalizacji kosztów", "", "## Reserved Instances"]
    candidates = analysis["reserved_candidates"]
    if candidates:
        for candidate in candidates:
            lines.append(
                f"- {candidate['instance_id']}: migracja do Reserved Instance, "
                f"oszczędność ${candidate['estimated_savings']:.2f}/miesiąc."
            )
    else:
        lines.append("- Nie wykryto kandydatów.")

    lines.extend(["", "## Zatrzymane instancje z wolumenami"])
    volumes = analysis["wasted_volumes"]
    if volumes:
        for volume in volumes:
            lines.append(
                f"- {volume['instance_id']} / {volume['volume_id']}: "
                f"${volume['monthly_cost']:.2f}/miesiąc do usunięcia lub odłączenia."
            )
    else:
        lines.append("- Nie wykryto marnotrawstwa wolumenów.")

    lines.extend(
        [
            "",
            "## Szacowana oszczędność",
            f"- ${analysis['estimated_monthly_savings']:.2f}/miesiąc.",
        ]
    )
    path = Path(output_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        temporary_path.replace(path)
    except OSError:
        temporary_path.unlink(missing_ok=True)
        raise
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Optymalizator kosztów chmurowych.")
    parser.add_argument("--output", default="cost_recommendations.md", help="Raport Markdown")
    args = parser.parse_args()

    try:
        analysis = analyze_costs(FAKE_INSTANCES)
        report = generate_report(analysis, args.output)
    except (OSError, ValueError) as error:
        print(f"Błąd analizy: {error}")
        return 1
    print(f"Utworzono raport: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
