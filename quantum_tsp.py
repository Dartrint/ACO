"""Qiskit QAOA solver for small Euclidean travelling-salesperson instances."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Sequence

import numpy as np
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from qiskit_aer.primitives import SamplerV2
from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_optimization.algorithms import MinimumEigenOptimizer
from qiskit_optimization.applications import Tsp

from aco_quantum import ACOConfig, AntColony, euclidean_distances, tour_length


@dataclass(frozen=True)
class QAOAConfig:
    reps: int = 1
    shots: int = 128
    maxiter: int = 8
    seed: int = 7

    def __post_init__(self) -> None:
        if not 1 <= self.reps <= 2:
            raise ValueError("QAOA depth must be 1 or 2")
        if not 64 <= self.shots <= 512:
            raise ValueError("QAOA shots must be between 64 and 512")
        if not 4 <= self.maxiter <= 30:
            raise ValueError("QAOA optimizer evaluations must be between 4 and 30")
        if self.seed < 0:
            raise ValueError("seed must be non-negative")


def solve_qaoa_tsp(
    distances: Sequence[Sequence[float]],
    config: QAOAConfig | None = None,
) -> dict[str, object]:
    """Solve a small TSP QUBO with QAOA and a local Qiskit Aer sampler."""
    settings = config or QAOAConfig()
    size = len(distances)
    if not 3 <= size <= 4 or any(len(row) != size for row in distances):
        raise ValueError("QAOA simulation supports square distance matrices of 3 or 4 cities")
    for i, row in enumerate(distances):
        for j, distance in enumerate(row):
            if not math.isfinite(distance) or distance < 0:
                raise ValueError("distances must be finite and non-negative")
            if i == j and distance != 0:
                raise ValueError("the distance from a city to itself must be zero")
            if not math.isclose(distance, distances[j][i], rel_tol=1e-9, abs_tol=1e-9):
                raise ValueError("TSP distances must be symmetric")

    tsp = Tsp(np.asarray(distances, dtype=float))
    problem = tsp.to_quadratic_program()
    backend = AerSimulator()
    pass_manager = generate_preset_pass_manager(optimization_level=1, backend=backend)
    energy_history: list[float] = []

    def record_energy(
        _evaluation: int,
        _parameters: np.ndarray,
        energy: float,
        _metadata: dict[str, object],
    ) -> None:
        energy_history.append(float(energy))

    qaoa = QAOA(
        sampler=SamplerV2(default_shots=settings.shots, seed=settings.seed),
        optimizer=COBYLA(maxiter=settings.maxiter),
        reps=settings.reps,
        callback=record_energy,
        transpiler=pass_manager,
    )
    started = time.perf_counter()
    result = MinimumEigenOptimizer(qaoa).solve(problem)
    elapsed = time.perf_counter() - started

    feasible_samples: list[dict[str, object]] = []
    best_tour: list[int] | None = None
    best_length: float | None = None
    for sample in result.samples:
        if sample.status.name != "SUCCESS":
            continue
        route = [int(city) for city in tsp.interpret(sample.x)]
        if len(route) != size or set(route) != set(range(size)):
            continue
        length = tour_length(tuple(route), distances)
        feasible_samples.append(
            {
                "tour": route,
                "distance": length,
            }
        )
        if best_length is None or length < best_length:
            best_tour, best_length = route, length

    return {
        "status": "feasible" if best_tour is not None else "no_feasible_sample",
        "tour": best_tour,
        "distance": best_length,
        "feasible_sample_count": len(feasible_samples),
        "feasible_samples": feasible_samples[:10],
        "qubits": problem.get_num_vars(),
        "reps": settings.reps,
        "shots": settings.shots,
        "optimizer_evaluations": len(energy_history),
        "energy_history": energy_history,
        "runtime_seconds": elapsed,
        "simulator": "Qiskit Aer · local CPU",
    }


def run_comparison(
    points: Sequence[tuple[float, float]],
    *,
    ants: int = 24,
    iterations: int = 80,
    alpha: float = 1.0,
    beta: float = 3.0,
    evaporation_rate: float = 0.5,
    seed: int | None = None,
    qaoa_config: QAOAConfig | None = None,
) -> dict[str, object]:
    if not 3 <= len(points) <= 4:
        raise ValueError("The local QAOA demo accepts 3 or 4 cities.")
    distances = euclidean_distances(points)
    colony = AntColony(
        distances,
        ACOConfig(
            ants=ants,
            iterations=iterations,
            alpha=alpha,
            beta=beta,
            evaporation_rate=evaporation_rate,
        ),
        seed=(qaoa_config or QAOAConfig()).seed if seed is None else seed,
    )

    started = time.perf_counter()
    aco_tour, aco_distance = colony.solve()
    aco_elapsed = time.perf_counter() - started
    qaoa_result = solve_qaoa_tsp(distances, qaoa_config)

    return {
        "city_count": len(points),
        "distances": distances,
        "aco": {
            "tour": list(aco_tour),
            "distance": aco_distance,
            "best_history": colony.best_history,
            "iterations": iterations,
            "runtime_seconds": aco_elapsed,
        },
        "qaoa": qaoa_result,
        "comparison_note": (
            "QAOA and ACO are different methods. A local simulator runtime is not "
            "evidence of quantum speedup; compare tour lengths only for feasible tours."
        ),
    }
