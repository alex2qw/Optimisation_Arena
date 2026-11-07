import numpy as np

from .base import BaseProblem


class Himmelblau(BaseProblem):
    def __init__(self):
        super().__init__("himmelblau", "Himmelblau", r"f(x,y)=(x^2+y-11)^2+(x+y^2-7)^2", "f(x, y) = (x² + y − 11)² + (x + y² − 7)²", "A multimodal landscape with four distinct global minima.", (-5.0, 5.0), ((3.0, 2.0), (-2.805118, 3.131312), (-3.779310, -3.283186), (3.584428, -1.848126)), unique_global_minimum=False, interpretation="Four equivalent global basins make the reached optimum depend on initialization and exploration.")

    def objective(self, point):
        x, y = np.asarray(point, dtype=float)
        return float((x * x + y - 11) ** 2 + (x + y * y - 7) ** 2)

    def vectorized_objective(self, x, y):
        return (x * x + y - 11) ** 2 + (x + y * y - 7) ** 2

    def gradient(self, point):
        x, y = np.asarray(point, dtype=float)
        a, b = x * x + y - 11, x + y * y - 7
        return np.array([4 * x * a + 2 * b, 2 * a + 4 * y * b], dtype=float)
