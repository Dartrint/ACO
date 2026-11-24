"""Local web server for the ACO/QAOA TSP experiment."""

from __future__ import annotations

import json
import logging
import math
import mimetypes
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import version
from pathlib import Path
from threading import Lock
from urllib.parse import urlsplit

from qiskit.exceptions import QiskitError
from qiskit_aer.aererror import AerError
from qiskit_algorithms.exceptions import AlgorithmError
from qiskit_optimization.exceptions import QiskitOptimizationError

from quantum_tsp import QAOAConfig, run_comparison


ROOT = Path(__file__).resolve().parent
STATIC_FILES = {
    "/": ROOT / "web" / "index.html",
    "/index.html": ROOT / "web" / "index.html",
    "/fonts/BarlowCondensed-Regular.ttf": ROOT / "web" / "fonts" / "BarlowCondensed-Regular.ttf",
    "/fonts/BarlowCondensed-Bold.ttf": ROOT / "web" / "fonts" / "BarlowCondensed-Bold.ttf",
    "/fonts/Almarai-Bold.ttf": ROOT / "web" / "fonts" / "Almarai-Bold.ttf",
    "/layout.css": ROOT / "web" / "layout.css",
}
MAX_REQUEST_BYTES = 16_384
RUN_LOCK = Lock()


def _bounded_int(settings: dict[str, object], name: str, minimum: int, maximum: int) -> int:
    value = settings.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer from {minimum} to {maximum}")
    return value


def _bounded_float(
    settings: dict[str, object],
    name: str,
    minimum: float,
    maximum: float,
) -> float:
    value = settings.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number from {minimum} to {maximum}")
    result = float(value)
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise ValueError(f"{name} must be a number from {minimum} to {maximum}")
    return result


@dataclass(frozen=True)
class ExperimentSettings:
    ants: int
    iterations: int
    alpha: float
    beta: float
    evaporation_rate: float
    seed: int
    qaoa: QAOAConfig


def _read_experiment(
    payload: object,
) -> tuple[list[tuple[float, float]], ExperimentSettings]:
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object")
    points = payload.get("points")
    settings = payload.get("settings")
    if not isinstance(points, list) or not 3 <= len(points) <= 4:
        raise ValueError("Provide coordinates for 3 or 4 cities")
    if not isinstance(settings, dict):
        raise ValueError("Experiment settings are required")

    coordinates: list[tuple[float, float]] = []
    for index, point in enumerate(points):
        if not isinstance(point, dict):
            raise ValueError(f"City {index + 1} must contain x and y coordinates")
        x = _bounded_float(point, "x", -1000, 1000)
        y = _bounded_float(point, "y", -1000, 1000)
        coordinates.append((x, y))

    seed = _bounded_int(settings, "seed", 0, 2**32 - 1)
    validated_settings = ExperimentSettings(
        ants=_bounded_int(settings, "ants", 4, 60),
        iterations=_bounded_int(settings, "iterations", 5, 200),
        alpha=_bounded_float(settings, "alpha", 0, 5),
        beta=_bounded_float(settings, "beta", 0, 8),
        evaporation_rate=_bounded_float(settings, "evaporation_rate", 0.05, 0.95),
        seed=seed,
        qaoa=QAOAConfig(
            reps=_bounded_int(settings, "reps", 1, 2),
            shots=_bounded_int(settings, "shots", 64, 512),
            maxiter=_bounded_int(settings, "maxiter", 4, 30),
            seed=seed,
        ),
    )
    return coordinates, validated_settings


class ExperimentHandler(BaseHTTPRequestHandler):
    server_version = "MetroOptimizationLab/1.0"

    def do_GET(self) -> None:
        route = urlsplit(self.path).path
        if route == "/api/health":
            self._send_json(
                200,
                {
                    "status": "ready",
                    "packages": {
                        "qiskit": version("qiskit"),
                        "qiskit-aer": version("qiskit-aer"),
                        "qiskit-algorithms": version("qiskit-algorithms"),
                        "qiskit-optimization": version("qiskit-optimization"),
                    },
                },
            )
            return

        file_path = STATIC_FILES.get(route)
        if file_path is None:
            self.send_error(404, "Resource not found")
            return
        if not file_path.is_file():
            self.send_error(404, "Resource not found")
            return
        body = file_path.read_bytes()
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/api/run":
            self.send_error(404, "Resource not found")
            return
        if not RUN_LOCK.acquire(blocking=False):
            self._send_json(409, {"error": "A simulation is already running. Wait for it to finish."})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0 or content_length > MAX_REQUEST_BYTES:
                self._send_json(413, {"error": "Request must be between 1 byte and 16 KB."})
                return
            payload = json.loads(self.rfile.read(content_length))
            points, settings = _read_experiment(payload)
            result = run_comparison(
                points,
                ants=settings.ants,
                iterations=settings.iterations,
                alpha=settings.alpha,
                beta=settings.beta,
                evaporation_rate=settings.evaporation_rate,
                seed=settings.seed,
                qaoa_config=settings.qaoa,
            )
            self._send_json(200, result)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self._send_json(400, {"error": str(error)})
        except (QiskitError, AerError, AlgorithmError, QiskitOptimizationError) as error:
            logging.exception("Quantum experiment failed")
            self._send_json(500, {"error": f"Qiskit experiment failed: {error}"})
        finally:
            RUN_LOCK.release()

    def _send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    server = ThreadingHTTPServer(("127.0.0.1", 8000), ExperimentHandler)
    print("Metro Optimization Lab: http://127.0.0.1:8000")
    print("Local only — close this terminal to stop the server.")
    server.serve_forever()


if __name__ == "__main__":
    main()
