from typing import Any

import numpy as np

from app.problems.base import BaseProblem


def generate_landscape(problem: BaseProblem, bounds: dict[str, tuple[float, float]], resolution: int) -> dict[str, Any]:
    x = np.linspace(bounds["x"][0], bounds["x"][1], resolution)
    y = np.linspace(bounds["y"][0], bounds["y"][1], resolution)
    xx, yy = np.meshgrid(x, y, indexing="xy")
    z = np.asarray(problem.vectorized_objective(xx, yy), dtype=float)
    if z.shape != (resolution, resolution) or not np.all(np.isfinite(z)):
        raise ValueError("landscape objective produced an invalid surface")
    return {
        "surface": {"x": x.tolist(), "y": y.tolist(), "z": z.tolist(), "resolution": resolution, "x_label": "x", "y_label": "y", "z_label": "f(x, y)"},
        "known_optima": [{"position": list(position), "objective_value": problem.minimum_value} for position in problem.global_minima],
    }
