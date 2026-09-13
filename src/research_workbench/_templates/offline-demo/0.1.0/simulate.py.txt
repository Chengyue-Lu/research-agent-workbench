"""Synthetic integer recurrence; no physical interpretation or scientific claim."""

import csv
import json
import sys
from pathlib import Path


def main():
    inputs = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    parameters = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    values = inputs["u"]
    initial, coefficient = parameters["x0"], parameters["a"]
    if (not isinstance(values, list) or len(values) > 1000
            or any(type(value) is not int for value in [initial, coefficient, *values])):
        raise ValueError("bounded integer inputs and parameters are required")
    target = Path(sys.argv[3]) / "trajectory.csv"
    state = initial
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["n", "x"])
        writer.writerow([0, state])
        for step, value in enumerate(values, 1):
            state = coefficient * state + value
            writer.writerow([step, state])


if __name__ == "__main__":
    main()
