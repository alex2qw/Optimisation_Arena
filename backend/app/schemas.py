from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def finite_number(value: float) -> float:
    if not isinstance(value, (int, float)) or not float(value) == float(value) or abs(float(value)) == float("inf"):
        raise ValueError("must be a finite number")
    return float(value)


class Bounds(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: tuple[float, float]
    y: tuple[float, float]

    @field_validator("x", "y")
    @classmethod
    def validate_axis(cls, value: tuple[float, float]) -> tuple[float, float]:
        low, high = map(finite_number, value)
        if low >= high:
            raise ValueError("lower bound must be less than upper bound")
        if high - low > 1000:
            raise ValueError("bounds span is unreasonably large")
        return (low, high)


class GradientDescentParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    learning_rate: float = Field(default=0.01, gt=0, le=10)
    tolerance: float = Field(default=1e-8, gt=0, le=1)
    patience: int = Field(default=30, ge=1, le=1000)


class SimulatedAnnealingParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    initial_temperature: float = Field(default=10.0, gt=0, le=1e8)
    cooling_rate: float = Field(default=0.99, gt=0, lt=1)
    proposal_scale: float = Field(default=0.5, gt=0, le=100)
    min_temperature: float = Field(default=1e-8, gt=0, le=1)


class GeneticAlgorithmParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    population_size: int = Field(default=50, ge=4, le=500)
    mutation_rate: float = Field(default=0.1, ge=0, le=1)
    mutation_strength: float = Field(default=0.2, gt=0, le=10)
    elite_count: int = Field(default=2, ge=1, le=100)
    tournament_size: int = Field(default=3, ge=2, le=20)

    @model_validator(mode="after")
    def validate_elites(self) -> "GeneticAlgorithmParameters":
        if self.elite_count >= self.population_size:
            raise ValueError("elite_count must be smaller than population_size")
        if self.tournament_size > self.population_size:
            raise ValueError("tournament_size cannot exceed population_size")
        return self


class LandscapeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resolution: int = Field(default=80, ge=10, le=250)


class ComparisonConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ranking_metric: Literal["best_score", "runtime", "balanced"] = "best_score"


class ExperimentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    function: str
    algorithms: list[str] = Field(min_length=1, max_length=3)
    iterations: int = Field(default=500, ge=1, le=10000)
    seed: int = Field(default=42, ge=-2_147_483_648, le=2_147_483_647)
    starting_point: tuple[float, float] | None = None
    bounds: Bounds | None = None
    parameters: dict[str, dict[str, Any]] = Field(default_factory=dict)
    landscape: LandscapeConfig = Field(default_factory=LandscapeConfig)
    comparison: ComparisonConfig = Field(default_factory=ComparisonConfig)
    repeated_trials: int = Field(default=1, ge=1, le=50)
    include_population_snapshots: bool = False
    max_evaluations: int | None = Field(default=None, ge=100, le=500000)

    @field_validator("function")
    @classmethod
    def normalize_function(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("algorithms")
    @classmethod
    def normalize_algorithms(cls, value: list[str]) -> list[str]:
        normalized = [item.strip().lower() for item in value]
        if len(set(normalized)) != len(normalized):
            raise ValueError("algorithms must not contain duplicates")
        return normalized

    @field_validator("starting_point")
    @classmethod
    def validate_point_numbers(cls, value: tuple[float, float] | None):
        if value is not None:
            return tuple(finite_number(item) for item in value)
        return value


class InsightRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    force_refresh: bool = False
