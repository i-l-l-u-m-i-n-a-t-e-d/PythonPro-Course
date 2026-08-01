import argparse
import json
import random
from pathlib import Path


def simulate_load() -> int:
    return random.randint(20, 90)


class AutoScalingSimulator:
    def __init__(self, load_provider=simulate_load):
        self.load_provider = load_provider
        self.history: list[dict[str, int | str]] = []
        self.high_measurements = 0
        self.low_measurements = 0

    def run(self, iterations: int = 20) -> list[dict[str, int | str]]:
        if iterations <= 0:
            raise ValueError("Liczba iteracji musi być dodatnia")

        for iteration in range(1, iterations + 1):
            cpu = self.load_provider()
            if not 20 <= cpu <= 90:
                raise ValueError("Obciążenie CPU musi być w zakresie 20-90%")

            action = "brak"
            if cpu > 70:
                self.high_measurements += 1
                self.low_measurements = 0
                if self.high_measurements == 3:
                    action = "uruchom nową instancję"
                    print(f"Iteracja {iteration}: CPU {cpu}% - uruchamiam nową instancję")
                    self.high_measurements = 0
            elif cpu < 30:
                self.low_measurements += 1
                self.high_measurements = 0
                if self.low_measurements == 3:
                    action = "zatrzymaj instancję"
                    print(f"Iteracja {iteration}: CPU {cpu}% - zatrzymuję instancję")
                    self.low_measurements = 0
            else:
                self.high_measurements = 0
                self.low_measurements = 0

            self.history.append({"iteration": iteration, "cpu_percent": cpu, "action": action})
        return self.history


def save_history(history: list[dict[str, int | str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary_path.replace(output_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Symulator Auto Scaling na podstawie obciążenia CPU.")
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--history-file", type=Path, default=Path("autoscaling_history.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.iterations <= 0:
        print("--iterations musi być dodatnie")
        return 1
    if args.seed is not None:
        random.seed(args.seed)

    simulator = AutoScalingSimulator()
    history = simulator.run(args.iterations)
    save_history(history, args.history_file)
    print(f"Zapisano historię {len(history)} iteracji: {args.history_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
