import numpy as np

from .base import BaseProblem


class Rastrigin(BaseProblem):
    def __init__(self):
        super().__init__("rastrigin", "Rastrigin", r"f(x,y)=20+x^2+y^2-10[\cos(2\pi x)+\cos(2\pi y)]", "f(x, y) = 20 + x² + y² − 10[cos(2πx) + cos(2πy)]", "A multimodal periodic landscape with many local minima.", (-5.12, 5.12), ((0.0, 0.0),), interpretation="Many local minima make global exploration valuable.")

    def objective(self, point):
        x, y = np.asarray(point, dtype=float)
        return float(20 + x * x + y * y - 10 * (np.cos(2 * np.pi * x) + np.cos(2 * np.pi * y)))

    def vectorized_objective(self, x, y):
        return 20 + x * x + y * y - 10 * (np.cos(2 * np.pi * x) + np.cos(2 * np.pi * y))

    def gradient(self, point):
        x, y = np.asarray(point, dtype=float)
        return np.array([2 * x + 20 * np.pi * np.sin(2 * np.pi * x), 2 * y + 20 * np.pi * np.sin(2 * np.pi * y)], dtype=float)
