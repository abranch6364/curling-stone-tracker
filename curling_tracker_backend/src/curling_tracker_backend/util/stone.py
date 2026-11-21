"""A tracked curling stone's data. Building a track (the Kalman filter) is StoneFilter in curling_shot_tracker.

This only needs numpy, so the read only server can load stones from the database without the tracking libraries.
"""
from dataclasses import dataclass, field
import enum
from typing import Optional, Tuple

import numpy as np


class StoneClass(enum.Enum):
    BLUE = 0
    GREEN = 1
    RED = 2
    YELLOW = 3


@dataclass
class Stone:
    """The track of one stone: its state at each time, and the measurements it was built from."""
    color: StoneClass
    time_history: list = field(default_factory=list)
    position_history: list = field(default_factory=list)
    velocity_history: list = field(default_factory=list)
    acceleration_history: list = field(default_factory=list)
    # The filter's state [x, y, vx, vy, ax, ay] and its covariance at each time
    state_history: list = field(default_factory=list)
    covariance_history: list = field(default_factory=list)
    # (time, position, standard deviation) of each measurement. Empty for a stone loaded from the database,
    # where only the track is stored.
    measurement_history: list = field(default_factory=list)

    @classmethod
    def from_db(cls, row) -> "Stone":
        """Rebuild a stone's track from its ShotStones row.

        Args:
            row: The row, with color, time_history, state_history and position_covariance_history

        Returns:
            Stone: The stone, with the stored position covariances as its covariance history
        """
        states = row["state_history"]
        return cls(color=StoneClass[row["color"].upper()],
                   time_history=row["time_history"].tolist(),
                   position_history=states[:, 0:2].tolist(),
                   velocity_history=states[:, 2:4].tolist(),
                   acceleration_history=states[:, 4:6].tolist(),
                   state_history=list(states),
                   covariance_history=list(row["position_covariance_history"]))

    @property
    def last_measurement_time(self) -> Optional[float]:
        if len(self.measurement_history) == 0:
            return None
        return self.measurement_history[-1][0]

    def get_max_velocity(self):
        if len(self.velocity_history) == 0:
            return 0.0
        return max(np.sqrt(v[0]**2 + v[1]**2) for v in self.velocity_history)

    def get_latest_position(self) -> Tuple[float, float]:
        return self.position_history[-1]

    def get_latest_time(self) -> float:
        return self.time_history[-1]

    def dict_for_json(self) -> dict:
        return {
            "color":
            self.color.name.lower(),
            "position_history":
            self.position_history,
            "velocity_history":
            self.velocity_history,
            "acceleration_history":
            self.acceleration_history,
            "time_history":
            self.time_history,
            "position_covariance_history": [
                covariance[:2, :2].tolist()
                for covariance in self.covariance_history
            ],
        }
