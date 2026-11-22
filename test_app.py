import unittest

from app import _read_experiment


def valid_payload() -> dict[str, object]:
    return {
        "points": [
            {"x": 0, "y": 0},
            {"x": 3, "y": 5},
            {"x": 6, "y": 1},
        ],
        "settings": {
            "ants": 24,
            "iterations": 80,
            "alpha": 1,
            "beta": 3,
            "evaporation_rate": 0.5,
            "seed": 7,
            "reps": 1,
            "shots": 128,
            "maxiter": 8,
        },
    }


class ExperimentRequestTests(unittest.TestCase):
    def test_reads_coordinates_and_algorithm_settings(self) -> None:
        points, settings = _read_experiment(valid_payload())
        self.assertEqual(points, [(0.0, 0.0), (3.0, 5.0), (6.0, 1.0)])
        self.assertEqual(settings.ants, 24)
        self.assertEqual(settings.qaoa.reps, 1)
        self.assertEqual(settings.qaoa.maxiter, 8)

    def test_rejects_coordinate_outside_supported_range(self) -> None:
        payload = valid_payload()
        payload["points"][0]["x"] = 1001
        with self.assertRaisesRegex(ValueError, "x must be a number"):
            _read_experiment(payload)

    def test_rejects_boolean_as_numeric_setting(self) -> None:
        payload = valid_payload()
        payload["settings"]["ants"] = True
        with self.assertRaisesRegex(ValueError, "ants must be an integer"):
            _read_experiment(payload)

    def test_rejects_more_cities_than_local_simulation_supports(self) -> None:
        payload = valid_payload()
        payload["points"].append({"x": 1, "y": 2})
        payload["points"].append({"x": 2, "y": 3})
        with self.assertRaisesRegex(ValueError, "3 or 4 cities"):
            _read_experiment(payload)


if __name__ == "__main__":
    unittest.main()
