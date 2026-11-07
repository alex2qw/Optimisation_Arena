import numpy as np

from .base import BaseProblem


class Rosenbrock(BaseProblem):
    def __init__(self):
        super().__init__("rosenbrock", "Rosenbrock", r"f(x,y)=(1-x)^2+100(y-x^2)^2", "f(x, y) = (1 − x)² + 100(y − x²)²", "A narrow curved valley that tests step-size control and exploitation.", (-2.048, 2.048), ((1.0, 1.0),), interpretation="The curved valley can make direct gradient steps slow or unstable.")

    def objective(self, point):
        x, y = np.asarray(point, dtype=float)
        return float((1 - x) ** 2 + 100 * (y - x * x) ** 2)

    def vectorized_objective(self, x, y):
        return (1 - x) ** 2 + 100 * (y - x * x) ** 2

    def gradient(self, point):
        x, y = np.asarray(point, dtype=float)
        return np.array([-2 * (1 - x) - 400 * x * (y - x * x), 200 * (y - x * x)], dtype=float)
