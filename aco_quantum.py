"""Classical ACO and quantum-inspired ACO for the travelling salesperson problem."""

from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass
from typing import Sequence


Tour = tuple[int, ...]


@dataclass(frozen=True)
class ACOConfig:
    ants: int = 24
    iterations: int = 150
    alpha: float = 1.0
    beta: float = 3.0
    evaporation_rate: float = 0.5
    pheromone_deposit: float = 1.0
    q0: float = 0.8
    elite_weight: float = 2.0
    quantum_strength: float = 1.5
    quantum_rotation: float = 0.08
    quantum_decay: float = 0.05

    def __post_init__(self) -> None:
        if self.ants < 1 or self.iterations < 1:
            raise ValueError("ants and iterations must be positive")
        if self.alpha < 0 or self.beta < 0:
            raise ValueError("alpha and beta must be non-negative")
        if not 0 < self.evaporation_rate < 1:
            raise ValueError("evaporation_rate must be between 0 and 1")
        if self.pheromone_deposit <= 0 or self.elite_weight < 0:
            raise ValueError("pheromone_deposit must be positive and elite_weight non-negative")
        if not 0 <= self.q0 <= 1:
            raise ValueError("q0 must be between 0 and 1")
        if self.quantum_strength < 0:
            raise ValueError("quantum_strength must be non-negative")
        if not 0 < self.quantum_rotation <= math.pi / 4:
            raise ValueError("quantum_rotation must be in (0, pi/4]")
        if not 0 <= self.quantum_decay <= 1:
            raise ValueError("quantum_decay must be between 0 and 1")


def validate_distances(distances: Sequence[Sequence[float]]) -> None:
    size = len(distances)
    if size < 3 or any(len(row) != size for row in distances):
        raise ValueError("distances must be a square matrix for at least 3 cities")
    for i, row in enumerate(distances):
        for j, distance in enumerate(row):
            if not math.isfinite(distance) or distance < 0:
                raise ValueError("distances must be finite and non-negative")
            if i == j and distance != 0:
                raise ValueError("the distance from a city to itself must be zero")


def tour_length(tour: Tour, distances: Sequence[Sequence[float]]) -> float:
    return sum(
        distances[tour[index]][tour[(index + 1) % len(tour)]]
        for index in range(len(tour))
    )


class AntColony:
    """Ant colony optimization with pheromone and heuristic edge scores."""

    def __init__(
        self,
        distances: Sequence[Sequence[float]],
        config: ACOConfig | None = None,
        seed: int | None = None,
    ) -> None:
        validate_distances(distances)
        self.distances = tuple(tuple(row) for row in distances)
        self.size = len(distances)
        self.config = config or ACOConfig()
        self.random = random.Random(seed)
        self.pheromone = [[1.0 for _ in range(self.size)] for _ in range(self.size)]
        self.best_history: list[float] = []

    def _edge_log_score(self, source: int, target: int) -> float:
        distance = max(self.distances[source][target], 1e-12)
        pheromone = max(self.pheromone[source][target], 1e-12)
        return self.config.alpha * math.log(pheromone) - self.config.beta * math.log(distance)

    def _choose_next(self, current: int, candidates: list[int]) -> int:
        scores = [self._edge_log_score(current, city) for city in candidates]
        maximum = max(scores)
        weights = [math.exp(score - maximum) for score in scores]
        if self.random.random() < self.config.q0:
            return candidates[max(range(len(candidates)), key=weights.__getitem__)]

        threshold = self.random.random() * sum(weights)
        for city, weight in zip(candidates, weights):
            threshold -= weight
            if threshold <= 0:
                return city
        return candidates[-1]

    def _construct_tour(self) -> Tour:
        start = self.random.randrange(self.size)
        tour = [start]
        unvisited = set(range(self.size))
        unvisited.remove(start)
        while unvisited:
            current = tour[-1]
            next_city = self._choose_next(current, sorted(unvisited))
            tour.append(next_city)
            unvisited.remove(next_city)
        return tuple(tour)

    def _update_pheromones(self, tours: list[tuple[Tour, float]]) -> None:
        retention = 1.0 - self.config.evaporation_rate
        for row in self.pheromone:
            for city in range(self.size):
                row[city] *= retention

        for tour, length in tours:
            deposit = self.config.pheromone_deposit / max(length, 1e-12)
            self._deposit(tour, deposit)

        iteration_best = min(tours, key=lambda result: result[1])
        self._deposit(
            iteration_best[0],
            self.config.elite_weight
            * self.config.pheromone_deposit
            / max(iteration_best[1], 1e-12),
        )

    def _deposit(self, tour: Tour, amount: float) -> None:
        for index, city in enumerate(tour):
            next_city = tour[(index + 1) % self.size]
            self.pheromone[city][next_city] += amount

    def _after_iteration(self, iteration_best: Tour) -> None:
        pass

    def solve(self) -> tuple[Tour, float]:
        best_tour: Tour | None = None
        best_length = math.inf
        self.best_history = []

        for _ in range(self.config.iterations):
            tours = [
                (tour, tour_length(tour, self.distances))
                for tour in (self._construct_tour() for _ in range(self.config.ants))
            ]
            iteration_best, iteration_length = min(tours, key=lambda result: result[1])
            if iteration_length < best_length:
                best_tour, best_length = iteration_best, iteration_length
            self.best_history.append(best_length)
            self._update_pheromones(tours)
            self._after_iteration(iteration_best)

        assert best_tour is not None
        return best_tour, best_length


class QuantumInspiredAntColony(AntColony):
    """ACO with a classical simulation of qubit-inspired edge probabilities.

    Each directed edge has an angle theta and probability sin(theta) ** 2.
    No quantum circuit or quantum hardware is used.
    """

    _ANGLE_EPSILON = 1e-4

    def __init__(
        self,
        distances: Sequence[Sequence[float]],
        config: ACOConfig | None = None,
        seed: int | None = None,
    ) -> None:
        super().__init__(distances, config, seed)
        neutral_angle = math.pi / 4
        self.angles = [
            [neutral_angle for _ in range(self.size)] for _ in range(self.size)
        ]

    def edge_probability(self, source: int, target: int) -> float:
        return math.sin(self.angles[source][target]) ** 2

    def _edge_log_score(self, source: int, target: int) -> float:
        aco_score = super()._edge_log_score(source, target)
        probability = max(self.edge_probability(source, target), self._ANGLE_EPSILON)
        return aco_score + self.config.quantum_strength * math.log(probability)

    def _after_iteration(self, iteration_best: Tour) -> None:
        selected_edges = {
            (city, iteration_best[(index + 1) % self.size])
            for index, city in enumerate(iteration_best)
        }
        neutral_angle = math.pi / 4
        rotation = self.config.quantum_rotation
        decay = self.config.quantum_decay

        for source in range(self.size):
            for target in range(self.size):
                if source == target:
                    continue
                angle = neutral_angle + (
                    self.angles[source][target] - neutral_angle
                ) * (1.0 - decay)
                if (source, target) in selected_edges:
                    angle = min(math.pi / 2 - self._ANGLE_EPSILON, angle + rotation)
                else:
                    angle = max(self._ANGLE_EPSILON, angle - rotation)
                self.angles[source][target] = angle


def euclidean_distances(points: Sequence[tuple[float, float]]) -> list[list[float]]:
    return [
        [
            math.hypot(x1 - x2, y1 - y2)
            for x2, y2 in points
        ]
        for x1, y1 in points
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--algorithm", choices=("aco", "qaco"), default="qaco")
    parser.add_argument("--iterations", type=int, default=150)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    points = [
        (0, 0), (2, 6), (5, 3), (6, 8), (8, 2),
        (1, 9), (9, 7), (4, 1), (7, 5), (3, 7),
    ]
    config = ACOConfig(iterations=args.iterations)
    colony_type = QuantumInspiredAntColony if args.algorithm == "qaco" else AntColony
    tour, length = colony_type(euclidean_distances(points), config, args.seed).solve()
    print(f"Algorithm: {args.algorithm}")
    print(f"Tour: {' -> '.join(map(str, tour + (tour[0],)))}")
    print(f"Total length: {length:.3f}")


if __name__ == "__main__":
    main()
