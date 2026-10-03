"""Splits a coarse scan of a full curling video into games, ends and shots.

The scan is the in-play stone detections from frames sampled every SCAN_INTERVAL_SECONDS across the
whole video. Shots are found from stones passing between the hog lines, which only happens while a
stone is being delivered. Play alternates direction every end, so ends are runs of shots delivered the
same way, and games are split where all the stones are brought back to the other end at once.
"""
from dataclasses import dataclass, field
import logging
from typing import List, Optional, Sequence, Tuple

import numpy as np

from curling_tracker_backend.util.sheet_coordinates import SHEET_COORDINATES

logger = logging.getLogger(__name__)

# Time (s) between the frames of the coarse scan
SCAN_INTERVAL_SECONDS = 1.0

# Distance (ft) of the hog lines from the centre of the sheet
HOG_LINE_Y = SHEET_COORDINATES["away_middle_hog"][1]

# A frame with at least this many stones between the hog lines is the stones being brought back to the
# other end after a game, not a delivery
STONE_RETURN_MIN_STONES = 3

# Delivery frames within this time (s) of a stone return are part of the return (stones are brought
# back a few at a time)
STONE_RETURN_MARGIN_SECONDS = 60.0

# Delivery frames closer together than this (s) belong to the same shot
SHOT_FRAME_GAP_SECONDS = 3.0

# Longest time (s) a delivered stone can go unseen between the hog lines (e.g. where no camera covers the
# middle of the sheet) and still be the same shot. A slow draw can take over 10s to cross the middle. The
# next stone of the same color is two deliveries later, well after this.
DELIVERY_MAX_GAP_SECONDS = 15.0

# A shot needs at least this many delivery frames, so a single false detection isn't a shot
MIN_DELIVERY_FRAMES = 2

# Slowest speed (ft/s) along the sheet of a delivered stone between the hog lines
MIN_DELIVERY_SPEED = 2.0

# Time (s) included before a shot's first delivery frame, so the whole delivery from the hack is in its
# window. The tracked shot is trimmed to when the delivered stone appears.
SHOT_PRE_PAD_SECONDS = 5.0

# Time (s) always included after a shot's last delivery frame, for the stone to travel into the house
SHOT_MIN_POST_SECONDS = 4.0

# Longest time (s) included after a shot's last delivery frame
SHOT_MAX_POST_SECONDS = 30.0

# Time (s) a shot's window has to end before the next shot's first delivery frame
SHOT_NEXT_GAP_SECONDS = 1.0

# A stone that moves less than this (ft) between scan frames is at rest
STATIONARY_TOL_FEET = 0.5

# A shot is over once this many scan frames in a row have no stone moving
SHOT_SETTLE_FRAMES = 3

# A gap (s) between shots longer than this starts a new game, for when the stones' return isn't seen
GAME_GAP_SECONDS = 15 * 60.0

# Every end has this many shots, half of each color
SHOTS_PER_END = 16

# Time (s) included in a tracked shot before the delivered stone's first measurement
SHOT_TRIM_PRE_SECONDS = 1.0

TO_AWAY = "to_away"
TO_HOME = "to_home"

# (color, x, y) of an in-play stone
ScanStone = Tuple[str, float, float]


@dataclass
class ScanFrame:
    time: float
    stones: List[ScanStone]


@dataclass
class ShotWindow:
    start_seconds: float
    end_seconds: float
    delivery_start: float
    delivery_end: float
    direction: str
    color: str


@dataclass
class SegmentedEnd:
    direction: str
    complete: bool
    shots: List[ShotWindow]

    @property
    def start_seconds(self) -> float:
        return self.shots[0].start_seconds

    @property
    def end_seconds(self) -> float:
        return self.shots[-1].end_seconds


@dataclass
class SegmentedGame:
    ends: List[SegmentedEnd] = field(default_factory=list)

    @property
    def start_seconds(self) -> float:
        return self.ends[0].start_seconds

    @property
    def end_seconds(self) -> float:
        return self.ends[-1].end_seconds


def between_hogs(stones: Sequence[ScanStone]) -> List[ScanStone]:
    """Gets the stones between the hog lines."""
    return [stone for stone in stones if abs(stone[2]) < HOG_LINE_Y]


def _has_moving_stone(frame: ScanFrame,
                      earlier_frames: Sequence[ScanFrame]) -> bool:
    """Check if a stone in a frame has moved, i.e. it isn't at rest where a stone of its color was in
    any of the earlier frames. Using a couple of earlier frames means a stone missed by the detector for
    a frame doesn't count as moving when it is seen again."""
    for color, x, y in frame.stones:
        at_rest = any(
            other_color == color and np.hypot(x - other_x, y -
                                              other_y) <= STATIONARY_TOL_FEET
            for earlier in earlier_frames
            for other_color, other_x, other_y in earlier.stones)
        if not at_rest:
            return True
    return False


def find_stone_returns(frames: Sequence[ScanFrame]) -> List[float]:
    """Find the times of frames showing the stones being brought back to the other end after a game."""
    return [
        frame.time for frame in frames
        if len(between_hogs(frame.stones)) >= STONE_RETURN_MIN_STONES
    ]


@dataclass
class DeliverySequence:
    """Consecutive scan frames with a stone of one color between the hog lines."""
    color: str
    frames: List[int]


def _delivery_sequences(
        frames: Sequence[ScanFrame],
        return_times: Sequence[float]) -> List[DeliverySequence]:
    """Group the frames with a stone being delivered into sequences, one per candidate shot. Each color has its
    own runs, so a stray detection of the other color doesn't change a delivery's direction."""
    sequences = []
    latest_sequence = {}
    for index, frame in enumerate(frames):
        between = between_hogs(frame.stones)
        if len(between) == 0 or len(between) >= STONE_RETURN_MIN_STONES:
            continue
        if any(
                abs(frame.time - return_time) <= STONE_RETURN_MARGIN_SECONDS
                for return_time in return_times):
            continue

        for color in {color for color, _, _ in between}:
            sequence = latest_sequence.get(color)
            if sequence is not None and frame.time - frames[
                    sequence.frames[-1]].time <= SHOT_FRAME_GAP_SECONDS:
                sequence.frames.append(index)
            else:
                latest_sequence[color] = DeliverySequence(color, [index])
                sequences.append(latest_sequence[color])
    return sequences


def _sequence_points(frames: Sequence[ScanFrame],
                     sequence: DeliverySequence) -> List[Tuple[float, float]]:
    """The (time, y) of each stone of the sequence's color between the hog lines in its frames."""
    return [(frames[index].time, y) for index in sequence.frames
            for color, _, y in between_hogs(frames[index].stones)
            if color == sequence.color]


def _speed(points: Sequence[Tuple[float, float]]) -> Optional[float]:
    """The speed (ft/s) along the sheet fitted to some points, or None if they're all at one time.
       This uses a line fit to a set of points and then returns the slope to find the speed."""
    times = [time for time, _ in points]
    if len(set(times)) < 2:
        return None
    return float(np.polyfit(times, [y for _, y in points], 1)[0])


def _same_delivery(frames: Sequence[ScanFrame], earlier: DeliverySequence,
                   later: DeliverySequence) -> bool:
    """Check if two runs of delivery frames are one stone that went unseen for a while between the hog
    lines: it has the same color and keeps travelling the same way, fast enough to be a delivery."""
    if earlier.color != later.color:
        return False

    first_end_time = frames[earlier.frames[-1]].time
    second_start_time = frames[later.frames[0]].time
    gap = second_start_time - first_end_time
    if not 0.0 < gap <= DELIVERY_MAX_GAP_SECONDS:
        return False

    #The returned sequence points can contain multiple detections of one stone at one time
    #due to having multiple cameras, so we use the mean to find the average of those detections/
    #This assumes that all detections of a color are the same stone between the hog lines, which
    #should generally be true.
    earlier_points = _sequence_points(frames, earlier)
    later_points = _sequence_points(frames, later)
    end_y = np.mean([y for t, y in earlier_points if t == first_end_time])
    start_y = np.mean([y for t, y in later_points if t == second_start_time])
    gap_speed = (start_y - end_y) / gap
    if abs(gap_speed) < MIN_DELIVERY_SPEED:
        return False

    # Check that the two sequences are in the same direction and match
    # What is expected based on the gap between them.
    for points in (earlier_points, later_points):
        speed = _speed(points)
        if speed is not None and abs(speed) >= MIN_DELIVERY_SPEED and np.sign(
                speed) != np.sign(gap_speed):
            return False
    return True


def _merge_delivery_sequences(
        frames: Sequence[ScanFrame],
        sequences: List[DeliverySequence]) -> List[DeliverySequence]:
    """Join runs of delivery frames that are one stone going unseen in the middle of the sheet. Each run
    is joined to the latest run of its color, so a stray detection of the other color in between doesn't
    stop it."""
    merged = []
    for sequence in sorted(sequences, key=lambda run: run.frames[0]):

        #Gets the previous sequence of the same color
        previous = next(
            (other
             for other in reversed(merged) if other.color == sequence.color),
            None)

        #If they are determined to be the same delivery, then merge them.
        if previous is not None and _same_delivery(frames, previous, sequence):
            previous.frames = previous.frames + sequence.frames
        else:
            merged.append(
                DeliverySequence(sequence.color, list(sequence.frames)))
    return sorted(merged, key=lambda run: run.frames[0])


def _settle_time(frames: Sequence[ScanFrame], last_index: int) -> float:
    """The time after a shot's last delivery frame when its stones have all come to rest."""
    last_time = frames[last_index].time
    still_frames = 0
    for index in range(last_index + 1, len(frames)):
        frame = frames[index]
        if frame.time - last_time > SHOT_MAX_POST_SECONDS:
            break
        earlier = frames[max(0, index - 2):index]
        still_frames = 0 if _has_moving_stone(frame,
                                              earlier) else still_frames + 1
        if still_frames >= SHOT_SETTLE_FRAMES and frame.time - last_time >= SHOT_MIN_POST_SECONDS:
            return frame.time
    return last_time + SHOT_MAX_POST_SECONDS


def find_shots(frames: Sequence[ScanFrame]) -> List[ShotWindow]:
    """Find the shots in a scan, each as the window of time to track it over.

    Args:
        frames (Sequence[ScanFrame]): The scan, in time order

    Returns:
        List[ShotWindow]: The shots in time order
    """
    return_times = find_stone_returns(frames)
    candidates = []
    sequences = _merge_delivery_sequences(
        frames, _delivery_sequences(frames, return_times))
    for sequence in sequences:
        if len(sequence.frames) < MIN_DELIVERY_FRAMES:
            continue

        speed = _speed(_sequence_points(frames, sequence))
        if speed is None or abs(speed) < MIN_DELIVERY_SPEED:
            continue

        candidates.append((sequence.frames, speed, sequence.color))

    shots = []
    for i, (sequence, speed, color) in enumerate(candidates):
        delivery_start = frames[sequence[0]].time
        delivery_end = frames[sequence[-1]].time
        end = _settle_time(frames, sequence[-1])
        if i + 1 < len(candidates):
            next_start = frames[candidates[i + 1][0][0]].time
            end = min(end, next_start - SHOT_NEXT_GAP_SECONDS)

        shots.append(
            ShotWindow(start_seconds=max(0.0, delivery_start -
                                         SHOT_PRE_PAD_SECONDS),
                       end_seconds=max(end, delivery_end),
                       delivery_start=delivery_start,
                       delivery_end=delivery_end,
                       direction=TO_AWAY if speed > 0 else TO_HOME,
                       color=color))
    return shots


def _create_end(direction: str, shots: List[ShotWindow]) -> SegmentedEnd:
    """Generate a SegmentedEnd from a list of shots."""
    colors = [shot.color for shot in shots]
    complete = len(shots) == SHOTS_PER_END and all(
        colors.count(color) == SHOTS_PER_END // 2 for color in set(colors))
    return SegmentedEnd(direction, complete, shots)


def segment_video(frames: Sequence[ScanFrame]) -> List[SegmentedGame]:
    """Split a scan of a full video into games, ends and shots.

    Args:
        frames (Sequence[ScanFrame]): The scan, in time order

    Returns:
        List[SegmentedGame]: The games in time order. Games without a full end are left out.
    """
    shots = find_shots(frames)
    return_times = find_stone_returns(frames)

    # Split the shots into games
    game_shots: List[List[ShotWindow]] = []
    for shot in shots:
        if game_shots:
            previous = game_shots[-1][-1]

            #Check if stones were returned between the previous shot and this shot
            returned = any(
                previous.delivery_end < return_time < shot.delivery_start
                for return_time in return_times)

            long_gap = shot.delivery_start - previous.delivery_end > GAME_GAP_SECONDS
            if not returned and not long_gap:
                game_shots[-1].append(shot)
                continue

        #Start a new game since stones were either returned to the other end
        #or there was a long gap between shots.
        game_shots.append([shot])

    #Take each game and split it into ends.
    #Ends are determined as a group of shots going in one direction.
    games = []
    for shots_in_game in game_shots:
        game = SegmentedGame()
        end_shots: List[ShotWindow] = []
        for shot in shots_in_game:
            if end_shots and shot.direction != end_shots[-1].direction:
                game.ends.append(
                    _create_end(end_shots[-1].direction, end_shots))
                end_shots = []
            end_shots.append(shot)

        #Make sure we add the last one as well, assuming it exists.
        if end_shots:
            game.ends.append(_create_end(end_shots[-1].direction, end_shots))

        if game.ends:
            games.append(game)
    return games


def find_delivered_stone(stones: Sequence, direction: str) -> Optional[int]:
    """Find the tracked stone that was delivered in a shot: the one that travels furthest in the
    direction of play, as long as it gets past the centre of the sheet.

    Args:
        stones (Sequence): The tracked stones, with time_history and position_history
        direction (str): The direction of play, TO_AWAY or TO_HOME

    Returns:
        Optional[int]: The index of the delivered stone, or None if no stone crossed the sheet.
    """
    sign = 1.0 if direction == TO_AWAY else -1.0
    best, best_travel = None, 0.0
    for index, stone in enumerate(stones):
        ys = [sign * position[1] for position in stone.position_history]
        if not ys or min(ys) > 0.0 or max(ys) < 0.0:
            continue
        travel = ys[-1] - ys[0]
        if travel > best_travel:
            best, best_travel = index, travel
    return best


def trim_start_time(stones: Sequence, direction: str,
                    window_start: float) -> Tuple[float, Optional[int]]:
    """The time a tracked shot should start: just before the delivered stone appears.

    Returns:
        Tuple[float, Optional[int]]: The start time, and the index of the delivered stone or None if it
            wasn't found (the start is then the window's start).
    """
    delivered = find_delivered_stone(stones, direction)
    if delivered is None:
        return window_start, None
    start = stones[delivered].time_history[0] - SHOT_TRIM_PRE_SECONDS
    return max(window_start, start), delivered
    start = stones[delivered].time_history[0] - SHOT_TRIM_PRE_SECONDS
    return max(window_start, start), delivered
