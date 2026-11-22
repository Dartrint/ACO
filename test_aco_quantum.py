import unittest

from aco_quantum import (
    ACOConfig,
    AntColony,
    QuantumInspiredAntColony,
    euclidean_distances,
    tour_length,
)


POINTS = [(0, 0), (2, 6), (5, 3), (6, 8), (8, 2), (1, 9)]
DISTANCES = euclidean_distances(POINTS)
CONFIG = ACOConfig(ants=8, iterations=12)


class AntColonyTests(unittest.TestCase):
    def test_both_algorithms_return_valid_deterministic_tours(self) -> None:
        for algorithm in (AntColony, QuantumInspiredAntColony):
            first = algorithm(DISTANCES, CONFIG, seed=3).solve()
            second = algorithm(DISTANCES, CONFIG, seed=3).solve()
            tour, length = first
            self.assertEqual(tour, second[0])
            self.assertEqual(len(tour), len(DISTANCES))
            self.assertEqual(set(tour), set(range(len(DISTANCES))))
            self.assertAlmostEqual(length, tour_length(tour, DISTANCES))
            self.assertEqual(length, second[1])

    def test_quantum_probability_is_updated_toward_iteration_best(self) -> None:
        colony = QuantumInspiredAntColony(DISTANCES, CONFIG, seed=1)
        initial_probability = colony.edge_probability(0, 1)
        colony._after_iteration((0, 1, 2, 3, 4, 5))
        self.assertGreater(colony.edge_probability(0, 1), initial_probability)
        self.assertLess(colony.edge_probability(0, 2), initial_probability)

    def test_rejects_non_square_distance_matrix(self) -> None:
        with self.assertRaises(ValueError):
            AntColony([[0, 1], [1]], CONFIG)


if __name__ == "__main__":
    unittest.main()
