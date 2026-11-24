import unittest
from unittest.mock import patch

from quantum_tsp import QAOAConfig, run_comparison, solve_qaoa_tsp


DISTANCES = [
    [0.0, 3.0, 4.0],
    [3.0, 0.0, 5.0],
    [4.0, 5.0, 0.0],
]


class QAOATests(unittest.TestCase):
    def test_comparison_uses_qaoa_seed_for_aco_when_seed_is_omitted(self) -> None:
        config = QAOAConfig(seed=19)
        with (
            patch("quantum_tsp.AntColony") as colony_type,
            patch("quantum_tsp.solve_qaoa_tsp", return_value={}),
        ):
            colony_type.return_value.solve.return_value = ((0, 1, 2), 12.0)
            run_comparison([(0, 0), (3, 0), (0, 4)], qaoa_config=config)

        self.assertEqual(colony_type.call_args.kwargs["seed"], 19)

    def test_runs_real_qaoa_on_aer_and_returns_decodable_samples(self) -> None:
        result = solve_qaoa_tsp(
            DISTANCES,
            QAOAConfig(reps=1, shots=64, maxiter=8, seed=5),
        )
        self.assertEqual(result["qubits"], 9)
        self.assertEqual(result["simulator"], "Qiskit Aer · local CPU")
        self.assertIn(result["status"], {"feasible", "no_feasible_sample"})
        self.assertGreaterEqual(
            result["feasible_sample_count"],
            len(result["feasible_samples"]),
        )
        self.assertGreaterEqual(result["runtime_seconds"], 0)
        if result["tour"] is not None:
            tour = result["tour"]
            self.assertEqual(set(tour), {0, 1, 2})
            self.assertEqual(result["distance"], 12.0)

    def test_rejects_oversized_simulation(self) -> None:
        distances = [[0 if row == column else 1 for column in range(5)] for row in range(5)]
        with self.assertRaisesRegex(ValueError, "3 or 4 cities"):
            solve_qaoa_tsp(distances)

    def test_rejects_asymmetric_distances(self) -> None:
        with self.assertRaisesRegex(ValueError, "symmetric"):
            solve_qaoa_tsp([[0, 1, 2], [2, 0, 3], [2, 3, 0]])

    def test_config_rejects_unreasonable_shots(self) -> None:
        with self.assertRaisesRegex(ValueError, "shots"):
            QAOAConfig(shots=10)


if __name__ == "__main__":
    unittest.main()
