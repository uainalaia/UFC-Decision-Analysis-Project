import math
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, frozen=True)


class Fighter(StrictModel):
    fighter_id: str
    fighter_name: str
    source_identifier: str


class Event(StrictModel):
    event_id: str
    event_name: str
    event_date: date
    location: str | None = None
    source_identifier: str


class Fight(StrictModel):
    fight_id: str
    event_id: str
    fighter_a_id: str
    fighter_b_id: str
    weight_class: str
    scheduled_rounds: Literal[3, 5]
    completed_rounds: int = Field(ge=1, le=5)
    result: Literal["a_win", "b_win"]
    victory_method: str
    finish_time: int = Field(ge=0, le=300)
    source_identifier: str

    @model_validator(mode="after")
    def coherent(self):
        if self.fighter_a_id == self.fighter_b_id:
            raise ValueError("A fighter cannot face themselves")
        if self.completed_rounds > self.scheduled_rounds:
            raise ValueError("Completed rounds exceed the scheduled format")
        if (self.completed_rounds - 1) * 300 + self.finish_time <= 0:
            raise ValueError("Fight exposure must be positive")
        return self


class TacticalPolicy(StrictModel):
    policy_id: str
    name: str
    description: str
    allocation: tuple[float, float, float]
    assumptions: str = "Planned opportunities, not guaranteed time in fight states."
    model_version: str = "0.1.0"

    @model_validator(mode="after")
    def simplex(self):
        if any(not 0 <= v <= 1 for v in self.allocation) or not math.isclose(
            sum(self.allocation), 1
        ):
            raise ValueError("Standing/clinch/ground allocation must be a probability simplex")
        return self


class ScenarioConfig(StrictModel):
    # C: scenario assumptions, log-odds units; not estimated treatment effects.
    striking_effect: float = Field(default=0, ge=-1.5, le=1.5)
    grappling_effect: float = Field(default=0, ge=-1.5, le=1.5)
    resistance: float = Field(default=0.5, ge=0, le=1)
    counter_cost: float = Field(default=0, ge=0, le=1)
    response_weights: tuple[float, float, float] = (0.25, 0.5, 0.25)
    effect_half_width: float = Field(default=0, ge=0, le=1.0)
    response_concentration: float | None = Field(default=None, ge=3, le=1000)

    @model_validator(mode="after")
    def distribution(self):
        if any(not 0 <= v <= 1 for v in self.response_weights) or not math.isclose(
            sum(self.response_weights), 1
        ):
            raise ValueError("Response weights must sum to one")
        if self.response_concentration and min(self.response_weights) <= 0:
            raise ValueError("Dirichlet uncertainty requires positive response weights")
        for value in (self.striking_effect, self.grappling_effect):
            if abs(value) + self.effect_half_width > 1.5 + 1e-12:
                raise ValueError("Effect uncertainty extends outside [-1.5, 1.5]")
        return self

    def changed(self, **updates):
        return ScenarioConfig(**(self.model_dump() | updates))


class AnalysisContext(StrictModel):
    fighter_a_id: str
    fighter_b_id: str
    reference_date: date
    weight_class: str
    scheduled_rounds: Literal[3, 5] = 5
    seed: int = Field(default=422, ge=0, le=2**32 - 1)
    draws: int = Field(default=5000, ge=100, le=100000)

    @model_validator(mode="after")
    def distinct(self):
        if self.fighter_a_id == self.fighter_b_id:
            raise ValueError("Choose two different fighters")
        return self
