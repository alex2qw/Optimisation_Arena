from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class BaseProblem(ABC):
    identifier: str
    name: str
    equation_latex: str
    equation_plain: str
    description: str
    default_bounds: tuple[float, float]
    global_minima: tuple[tuple[float, float], ...]
    minimum_value: float = 0.0
    unique_global_minimum: bool = True
    interpretation: str = "Lower objective values indicate better solutions."

    @abstractmethod
    def objective(self, point: np.ndarray | tuple[float, float]) -> float:
        raise NotImplementedError

    @abstractmethod
    def vectorized_objective(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    @abstractmethod
    def gradient(self, point: np.ndarray | tuple[float, float]) -> np.ndarray:
        raise NotImplementedError

    def metadata(self, bounds: dict[str, list[float]] | None = None) -> dict[str, Any]:
        selected = bounds or {"x": list(self.default_bounds), "y": list(self.default_bounds)}
        return {
            "identifier": self.identifier,
            "name": self.name,
            "equation_latex": self.equation_latex,
            "equation_plain": self.equation_plain,
            "description": self.description,
            "dimension": 2,
            "bounds": selected,
            "global_minima": [{"position": list(point), "objective_value": self.minimum_value} for point in self.global_minima],
            "global_minimum_value": self.minimum_value,
            "unique_global_minimum": self.unique_global_minimum,
            "interpretation": self.interpretation,
        }


def _load_problems() -> dict[str, BaseProblem]:
    from .himmelblau import Himmelblau
    from .rastrigin import Rastrigin
    from .rosenbrock import Rosenbrock
    from .sphere import Sphere

    problems = [Sphere(), Rosenbrock(), Rastrigin(), Himmelblau()]
    return {problem.identifier: problem for problem in problems}


PROBLEMS = _load_problems()


def get_problem(identifier: str) -> BaseProblem:
    try:
        return PROBLEMS[identifier.lower()]
    except KeyError as exc:
        raise ValueError(f"Unsupported function: {identifier}") from exc


def list_problems() -> list[BaseProblem]:
    return list(PROBLEMS.values())
