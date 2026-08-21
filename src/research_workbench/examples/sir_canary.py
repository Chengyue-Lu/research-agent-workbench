"""Deterministic standard-library SIR numerical verification canary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


State = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class SirRun:
    beta: float
    gamma: float
    population: float
    dt: float
    method: str
    states: tuple[State, ...]

    @property
    def peak_infected(self) -> float:
        return max(state[1] for state in self.states)


def _derivative(state: State, beta: float, gamma: float, population: float) -> State:
    susceptible, infected, _removed = state
    incidence = beta * susceptible * infected / population
    return -incidence, incidence - gamma * infected, gamma * infected


def _add(state: State, delta: State, scale: float) -> State:
    return tuple(value + scale * change for value, change in zip(state, delta, strict=True))  # type: ignore[return-value]


def _euler_step(state: State, dt: float, beta: float, gamma: float, population: float) -> State:
    return _add(state, _derivative(state, beta, gamma, population), dt)


def _rk4_step(state: State, dt: float, beta: float, gamma: float, population: float) -> State:
    derivative: Callable[[State], State] = lambda value: _derivative(value, beta, gamma, population)
    k1 = derivative(state)
    k2 = derivative(_add(state, k1, dt / 2.0))
    k3 = derivative(_add(state, k2, dt / 2.0))
    k4 = derivative(_add(state, k3, dt))
    return tuple(
        value + dt * (a + 2.0 * b + 2.0 * c + d) / 6.0
        for value, a, b, c, d in zip(state, k1, k2, k3, k4, strict=True)
    )  # type: ignore[return-value]


def simulate_sir(
    *,
    beta: float = 0.3,
    gamma: float = 0.1,
    population: float = 1000.0,
    initial: State = (999.0, 1.0, 0.0),
    dt: float = 1.0,
    days: float = 160.0,
    method: str = "euler",
) -> SirRun:
    if beta < 0 or gamma < 0 or population <= 0 or dt <= 0 or days <= 0:
        raise ValueError("rates must be non-negative and population/dt/days positive")
    if abs(sum(initial) - population) > 1e-9 or min(initial) < 0:
        raise ValueError("initial state must be non-negative and conserve population")
    steps_float = days / dt
    if abs(steps_float - round(steps_float)) > 1e-9:
        raise ValueError("days must be an integer multiple of dt")
    step = {"euler": _euler_step, "rk4": _rk4_step}.get(method)
    if step is None:
        raise ValueError("method must be euler or rk4")
    states = [initial]
    for _ in range(round(steps_float)):
        next_state = step(states[-1], dt, beta, gamma, population)
        states.append(next_state)
    return SirRun(beta, gamma, population, dt, method, tuple(states))


def verification_report() -> dict[str, object]:
    reference = simulate_sir(dt=0.01, method="rk4")
    euler_runs = tuple(simulate_sir(dt=dt, method="euler") for dt in (1.0, 0.5, 0.25))

    def final_error(run: SirRun) -> float:
        return sum(abs(value - target) for value, target in zip(run.states[-1], reference.states[-1], strict=True))

    errors = tuple(final_error(run) for run in euler_runs)
    all_runs = (reference, *euler_runs)
    conservation_error = max(abs(sum(state) - run.population) for run in all_runs for state in run.states)
    minimum_compartment = min(value for run in all_runs for state in run.states for value in state)
    sensitivity = {
        label: simulate_sir(beta=beta, dt=0.05, method="rk4").peak_infected
        for label, beta in (("beta_minus_10pct", 0.27), ("baseline", 0.3), ("beta_plus_10pct", 0.33))
    }
    checks = {
        "population_conserved": conservation_error < 1e-8,
        "non_negative": minimum_compartment >= -1e-12,
        "euler_converges_toward_rk4": errors[2] < errors[1] < errors[0],
        "beta_sensitivity_ordered": sensitivity["beta_minus_10pct"] < sensitivity["baseline"] < sensitivity["beta_plus_10pct"],
    }
    return {
        "case_id": "SIM-" + "SIR" + "-001",
        "parameters": {"population": 1000.0, "initial": [999.0, 1.0, 0.0], "beta": 0.3, "gamma": 0.1, "days": 160.0},
        "reference": {"method": "rk4", "dt": 0.01},
        "euler_final_l1_errors": {str(run.dt): error for run, error in zip(euler_runs, errors, strict=True)},
        "maximum_conservation_error": conservation_error,
        "minimum_compartment": minimum_compartment,
        "peak_infected_sensitivity": sensitivity,
        "checks": checks,
        "status": "passed" if all(checks.values()) else "failed",
        "claim_ceiling": "supports only numerical properties of this fixed deterministic SIR fixture",
        "human_gate": "any inference about a real epidemic, population, intervention, or forecast",
    }
