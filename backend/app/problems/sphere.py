import numpy as np

from .base import BaseProblem


class Sphere(BaseProblem):
    def __init__(self):
        super().__init__("sphere", "Sphere", r"f(x,y)=x^2+y^2", "f(x, y) = x² + y²", "A smooth convex bowl with one optimum.", (-5.12, 5.12), ((0.0, 0.0),), interpretation="A simple baseline where gradient-based search should be highly effective.")

    def objective(self, point):
        x, y = np.asarray(point, dtype=float)
        return float(x * x + y * y)

    def vectorized_objective(self, x, y):
        return x * x + y * y

    def gradient(self, point):
        x, y = np.asarray(point, dtype=float)
        return np.array([2 * x, 2 * y], dtype=float)
