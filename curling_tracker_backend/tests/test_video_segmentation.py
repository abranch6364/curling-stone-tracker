from types import SimpleNamespace

import pytest

import curling_tracker_backend.util.video_segmentation as segmentation
from curling_tracker_backend.util.video_segmentation import ScanFrame, TO_AWAY, TO_HOME

# Seconds a synthetic delivery takes from the near back line to the far house
DELIVERY_SECONDS = 12
START_Y, END_Y = -60.0, 55.0


class ScanBuilder:
    """Builds a synthetic scan, one frame per second, of stones being delivered and coming to rest."""

    def __init__(self, hidden_middle_feet=0.0):
        self.events = []  # (time, kind, payload)
        self.time = 0
        # Moving stones within this distance (ft) of the centre line aren't seen, like a sheet whose
        # middle no camera covers
        self.hidden_middle_feet = hidden_middle_feet

    def shot(self, direction, color, wait=30):
        self.events.append((self.time, "shot", (direction, color)))
        self.time += wait

    def end(self, direction, wait_after=60, colors=("green", "yellow")):
        for i in range(segmentation.SHOTS_PER_END):
            self.shot(direction, colors[i % 2])
        self.events.append((self.time - 10, "clear", None))
        self.time += wait_after

    def stone_return(self, wait_after=120):
        self.events.append((self.time, "return", None))
        self.time += wait_after

    def wait(self, seconds):
        self.time += seconds

    def build(self):
        resting = []
        moving = []  # (start time, sign, color, x)
        returning_until = -1
        frames = []
        events = sorted(self.events, key=lambda e: e[0])
        event_index = 0
        for t in range(self.time + DELIVERY_SECONDS + 5):
            while event_index < len(events) and events[event_index][0] <= t:
                _, kind, payload = events[event_index]
                event_index += 1
                if kind == "shot":
                    direction, color = payload
                    sign = 1.0 if direction == TO_AWAY else -1.0
                    x = -6.0 + 0.8 * (len(resting) + len(moving))
                    moving.append((t, sign, color, x))
                elif kind == "clear":
                    resting = []
                elif kind == "return":
                    returning_until = t + 3

            stones = list(resting)
            still_moving = []
            for start, sign, color, x in moving:
                fraction = (t - start) / DELIVERY_SECONDS
                y = START_Y + (END_Y - START_Y) * min(fraction, 1.0)
                if fraction >= 1.0:
                    resting.append((color, x, sign * END_Y))
                    stones.append((color, x, sign * END_Y))
                else:
                    if abs(y) >= self.hidden_middle_feet:
                        stones.append((color, x, sign * y))
                    still_moving.append((start, sign, color, x))
            moving = still_moving

            if t <= returning_until:
                stones += [("green", -5.0 + i, 10.0 + i) for i in range(8)]

            frames.append(ScanFrame(float(t), stones))
        return frames


def test_crossing_stone_is_a_shot_window_with_pre_pad():
    builder = ScanBuilder()
    builder.wait(20)
    builder.shot(TO_AWAY, "green")
    shots = segmentation.find_shots(builder.build())

    assert len(shots) == 1
    shot = shots[0]
    assert shot.direction == TO_AWAY
    assert shot.color == "green"
    assert shot.start_seconds == pytest.approx(
        shot.delivery_start - segmentation.SHOT_PRE_PAD_SECONDS)
    # The stone comes to rest in the far house after leaving the hog lines
    assert shot.end_seconds > 20 + DELIVERY_SECONDS
    assert shot.end_seconds <= shot.delivery_end + segmentation.SHOT_MAX_POST_SECONDS


def test_stone_unseen_in_the_middle_is_one_shot():
    builder = ScanBuilder(hidden_middle_feet=25.0)
    builder.wait(20)
    builder.shot(TO_AWAY, "green")
    frames = builder.build()

    # The stone is only seen between the hog lines at either end, with a gap longer than a shot's merge gap
    delivery_times = [
        frame.time for frame in frames
        if segmentation.between_hogs(frame.stones)
    ]
    assert max(b - a for a, b in zip(delivery_times, delivery_times[1:])
               ) > segmentation.SHOT_FRAME_GAP_SECONDS

    shots = segmentation.find_shots(frames)
    assert len(shots) == 1
    assert shots[0].direction == TO_AWAY
    assert shots[0].delivery_start == delivery_times[0]
    assert shots[0].delivery_end == delivery_times[-1]


def test_slow_stone_unseen_in_the_middle_is_one_shot():
    # The between-hog detections of a real slow draw (game 2, end 6), which went unseen for 11s
    resting = [("green", 2.6, -43.0), ("green", -2.9, -60.9),
               ("yellow", -2.6, -56.5)]
    seen = {
        13688: 33.4,
        13689: 26.5,
        13690: 19.4,
        13701: -24.3,
        13702: -27.4,
        13703: -30.1,
        13705: -34.5
    }
    frames = [
        ScanFrame(float(t),
                  resting + ([("yellow", 0.0, seen[t])] if t in seen else []))
        for t in range(13670, 13721)
    ]

    shots = segmentation.find_shots(frames)

    assert len(shots) == 1
    assert shots[0].direction == TO_HOME
    assert shots[0].color == "yellow"
    assert (shots[0].delivery_start, shots[0].delivery_end) == (13688.0,
                                                                13705.0)


def test_stray_detection_of_other_color_does_not_split_delivery():
    # The between-hog detections at the end of a real end (game 2, end 3): a yellow delivery unseen in the
    # middle, then a stray green detection 2s later, then the end's last four deliveries
    seen = {
        11049: ("yellow", -32.5),
        11050: ("yellow", -24.3),
        11051: ("yellow", -15.9),
        11057: ("yellow", 12.2),
        11058: ("yellow", 18.0),
        11059: ("yellow", 23.5),
        11060: ("yellow", 28.5),
        11061: ("yellow", 33.3),
        11063: ("green", -24.5),
        11116: ("green", -30.2),
        11117: ("green", -21.8),
        11118: ("green", -13.3),
        11124: ("green", 17.5),
        11125: ("green", 23.9),
        11126: ("green", 29.4),
        11127: ("green", 34.7),
        11224: ("yellow", -31.8),
        11225: ("yellow", -23.9),
        11226: ("yellow", -16.1),
        11233: ("yellow", 17.0),
        11234: ("yellow", 21.5),
        11235: ("yellow", 27.0),
        11236: ("yellow", 32.0),
        11269: ("green", -34.5),
        11270: ("green", -26.6),
        11271: ("green", -18.2),
        11278: ("green", 17.5),
        11279: ("green", 22.8),
        11280: ("green", 28.1),
        11281: ("green", 32.8),
    }
    frames = [
        ScanFrame(float(t),
                  [(seen[t][0], 0.0, seen[t][1])] if t in seen else [])
        for t in range(11030, 11300)
    ]

    shots = segmentation.find_shots(frames)

    assert [(shot.delivery_start, shot.delivery_end, shot.color)
            for shot in shots] == [
                (11049.0, 11061.0, "yellow"),
                (11116.0, 11127.0, "green"),
                (11224.0, 11236.0, "yellow"),
                (11269.0, 11281.0, "green"),
            ]
    assert all(shot.direction == TO_AWAY for shot in shots)


def test_shot_waits_for_stone_unseen_until_past_far_hog():
    # A real delivery (game 1, end 1, shot 7) whose stone is never seen in the far half between the hog
    # lines: it is last seen at y -15.3 at 516s and next past the far hog at 528s, then it pushes a green
    delivered = {
        511: (0.5, -56.6), 512: (0.7, -48.3), 513: (0.9, -39.8), 514: (1.3, -31.8), 515: (1.5, -23.5),
        516: (1.6, -15.3), 528: (1.4, 38.5), 529: (1.1, 41.9), 531: (0.5, 45.9), 532: (0.0, 47.7),
    }
    resting = [("green", -0.6, 49.5), ("green", 0.5, 54.1), ("yellow", 0.3, 40.1), ("yellow", 3.7, 59.3)]
    frames = []
    for t in range(500, 556):
        stones = list(resting)
        if t in delivered:
            stones.append(("green", *delivered[t]))
        elif t >= 533:
            stones.append(("green", -0.2, 48.7))
        # The green the delivered stone hits
        stones.append(("green", -0.7, 49.7) if t < 533 else ("green", -1.2, 50.8) if t == 533 else ("green", -1.3, 51.1))
        frames.append(ScanFrame(float(t), stones))

    shots = segmentation.find_shots(frames)

    assert len(shots) == 1
    assert (shots[0].delivery_start, shots[0].delivery_end) == (514.0, 516.0)
    # The window lasts until the stones have stopped after the delivered stone arrives, not until the
    # first still frames while it is unseen in the middle
    assert shots[0].end_seconds >= 536.0


def test_shot_ends_after_stone_stops_short_between_hogs():
    # A stone that stops between the hog lines, in view, and is then taken out of play
    seen = {100: -30.0, 101: -20.0, 102: -10.0, 103: 0.0, 104: 8.0, 105: 14.0, 106: 18.0, 107: 20.0,
            108: 20.1, 109: 20.0, 110: 20.1}
    frames = [ScanFrame(float(t), [("yellow", 0.0, seen[t])] if t in seen else []) for t in range(90, 160)]

    shots = segmentation.find_shots(frames)

    assert len(shots) == 1
    assert shots[0].delivery_end == 110.0
    assert shots[0].end_seconds < shots[0].delivery_end + 10.0


def test_ends_with_stones_unseen_in_the_middle():
    builder = ScanBuilder(hidden_middle_feet=25.0)
    builder.end(TO_AWAY)
    builder.end(TO_HOME)
    games = segmentation.segment_video(builder.build())

    assert len(games) == 1
    assert [len(end.shots) for end in games[0].ends] == [16, 16]
    assert all(end.complete for end in games[0].ends)
    # Each shot is the whole delivery, seen at both ends of the hidden middle, not one of its halves
    for end in games[0].ends:
        for shot in end.shots:
            assert shot.delivery_end - shot.delivery_start > segmentation.SHOT_FRAME_GAP_SECONDS


def test_direction_flip_starts_a_new_end():
    builder = ScanBuilder()
    builder.end(TO_AWAY)
    builder.end(TO_HOME)
    games = segmentation.segment_video(builder.build())

    assert len(games) == 1
    assert [end.direction for end in games[0].ends] == [TO_AWAY, TO_HOME]
    assert all(end.complete for end in games[0].ends)
    assert all(len(end.shots) == 16 for end in games[0].ends)


def test_incomplete_end_is_flagged():
    builder = ScanBuilder()
    for i in range(12):
        builder.shot(TO_AWAY, ("green", "yellow")[i % 2])
    games = segmentation.segment_video(builder.build())

    assert len(games[0].ends) == 1
    assert not games[0].ends[0].complete


def test_stone_return_starts_a_new_game():
    builder = ScanBuilder()
    builder.end(TO_AWAY)
    builder.end(TO_HOME)
    builder.stone_return()
    builder.end(TO_HOME)
    games = segmentation.segment_video(builder.build())

    assert len(games) == 2
    assert [len(game.ends) for game in games] == [2, 1]


def test_long_gap_starts_a_new_game():
    builder = ScanBuilder()
    builder.end(TO_AWAY)
    builder.wait(int(segmentation.GAME_GAP_SECONDS) + 60)
    builder.end(TO_AWAY)
    games = segmentation.segment_video(builder.build())

    assert len(games) == 2


def test_single_flicker_is_not_a_shot():
    frames = [ScanFrame(float(t), [("green", 1.0, 57.0)]) for t in range(60)]
    frames[30] = ScanFrame(30.0, [("green", 1.0, 57.0), ("yellow", 0.0, 5.0)])

    assert segmentation.find_shots(frames) == []


def test_stone_resting_between_hogs_is_not_a_shot():
    frames = [ScanFrame(float(t), [("green", 1.0, 20.0)]) for t in range(60)]

    assert segmentation.find_shots(frames) == []


def _stone(times, ys):
    return SimpleNamespace(time_history=list(times),
                           position_history=[(0.0, y) for y in ys])


def test_trim_start_uses_delivered_stone():
    resting = _stone(range(100, 120), [55.0] * 20)
    delivered = _stone(range(104, 120), [-60.0 + 7.0 * i for i in range(16)])

    start, index = segmentation.trim_start_time([resting, delivered], TO_AWAY,
                                                100.0)

    assert index == 1
    assert start == pytest.approx(104 - segmentation.SHOT_TRIM_PRE_SECONDS)


def test_trim_start_without_delivered_stone_keeps_window():
    resting = _stone(range(100, 120), [55.0] * 20)

    assert segmentation.trim_start_time([resting], TO_AWAY,
                                        100.0) == (100.0, None)


def _moving_stone(start_y, speed, seconds, sign=1.0):
    """A stone moving at a constant speed (ft/s) in the direction of play, sampled every 0.1s."""
    times = [i / 10 for i in range(int(seconds * 10) + 1)]
    return SimpleNamespace(time_history=times,
                           position_history=[(0.0, sign * (start_y + speed * t)) for t in times],
                           velocity_history=[(0.0, sign * speed)] * len(times))


@pytest.mark.parametrize("direction, sign", [(TO_AWAY, 1.0), (TO_HOME, -1.0)])
def test_split_times(direction, sign):
    # Starts 1 ft inside the back line at 10 ft/s, so it crossed the back line 0.1s before its track starts
    stone = _moving_stone(-62.0, 10.0, 12.0, sign)

    back_line_to_hog, hog_to_hog = segmentation.split_times(stone, direction)

    assert back_line_to_hog == pytest.approx(2.7)
    assert hog_to_hog == pytest.approx(7.2)


def test_no_hog_to_hog_time_for_stone_stopping_short():
    stone = _moving_stone(-62.0, 10.0, 8.0)
    stone.position_history = [(0.0, min(y, 20.0)) for _, y in stone.position_history]

    back_line_to_hog, hog_to_hog = segmentation.split_times(stone, TO_AWAY)

    assert back_line_to_hog == pytest.approx(2.7)
    assert hog_to_hog is None


def test_no_back_line_to_hog_time_for_track_starting_far_inside_back_line():
    stone = _moving_stone(-50.0, 10.0, 10.0)

    back_line_to_hog, hog_to_hog = segmentation.split_times(stone, TO_AWAY)

    assert back_line_to_hog is None
    assert hog_to_hog == pytest.approx(7.2)
