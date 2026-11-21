import numpy as np

from curling_tracker_backend.util.stone import Stone, StoneClass
from curling_tracker_backend.util.video_segmentation import TO_AWAY, TO_HOME, find_delivered_stone


def shot_stone_row(color, start_y, end_y, samples=50):
    """A ShotStones row, as the database returns it, of a stone moving along the sheet at a steady speed."""
    times = np.linspace(100.0, 110.0, samples)
    ys = np.linspace(start_y, end_y, samples)
    speed = (end_y - start_y) / (times[-1] - times[0])
    states = np.zeros((samples, 6))
    states[:, 0] = 0.5
    states[:, 1] = ys
    states[:, 3] = speed
    covariances = np.tile(np.array([[0.04, 0.01], [0.01, 0.09]]), (samples, 1, 1))
    return {
        "color": color,
        "time_history": times,
        "state_history": states,
        "position_covariance_history": covariances,
    }


def test_from_db_gives_the_stored_track():
    row = shot_stone_row("yellow", -60.0, 55.0)
    stone = Stone.from_db(row)

    assert stone.color == StoneClass.YELLOW
    # The same JSON the shot endpoint sent before stones were loaded as Stones
    assert stone.dict_for_json() == {
        "color": "yellow",
        "position_history": row["state_history"][:, 0:2].tolist(),
        "velocity_history": row["state_history"][:, 2:4].tolist(),
        "acceleration_history": row["state_history"][:, 4:6].tolist(),
        "time_history": row["time_history"].tolist(),
        "position_covariance_history": row["position_covariance_history"].tolist(),
    }
    assert stone.measurement_history == []
    assert stone.last_measurement_time is None


def test_find_delivered_stone_on_loaded_stones():
    resting = Stone.from_db(shot_stone_row("red", 55.0, 55.0))
    to_away = Stone.from_db(shot_stone_row("yellow", -60.0, 55.0))
    to_home = Stone.from_db(shot_stone_row("red", 60.0, -55.0))

    assert find_delivered_stone([resting, to_away], TO_AWAY) == 1
    assert find_delivered_stone([to_home, resting], TO_HOME) == 0
    assert find_delivered_stone([resting], TO_AWAY) is None
