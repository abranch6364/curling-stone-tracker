import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Badge, Box, Button, Grid, HStack, NativeSelect, Spinner, Stack, Text, VStack } from "@chakra-ui/react";

import ShotViewer from "../ShotViewer/ShotViewer";

import {
  POLL_INTERVAL_MS,
  STATUS_COLORS,
  VideoLink,
  fetchJson,
  formatDrawStart,
  formatSplitTimes,
  formatVideoTime,
  isFinished,
  trackingRunsQuery,
  videoName,
} from "../../utility/TrackingRunHelper";
import useIsPhone from "../../utility/useIsPhone";

const SELECTED_GAME_STORAGE_KEY = "fullVideoTracking.selectedGameId";
const DIRECTION_LABELS = { to_away: "→ away", to_home: "← home" };
// Shot chips are bigger on a phone, to be easier to tap
const CHIP_SIZE = { base: "sm", md: "xs" };
// At most this many shot chips per line: an end's 16 shots are two lines of 8, or one line on a desktop, where
// they're beside the end dropdown
const CHIP_COLUMNS = {
  base: "repeat(8, minmax(0, 1fr))",
  md: "repeat(8, auto)",
  lg: "repeat(16, auto)",
};
// On a phone the chips share the width of their line equally, so 8 always fit
const CHIP_WIDTH = { base: "100%", md: "auto" };

const loadSelectedGame = () => {
  try {
    return localStorage.getItem(SELECTED_GAME_STORAGE_KEY);
  } catch {
    return null;
  }
};

const saveSelectedGame = (gameId) => {
  try {
    localStorage.setItem(SELECTED_GAME_STORAGE_KEY, gameId);
  } catch {
    // Remembering the draw is only a convenience
  }
};

const ShotChip = ({ shot, selected, runFinished, onClick }) => {
  if (shot.status === "pending") {
    // A plain grey chip, since every shot is pending while a run tracks. A run that stopped early (e.g.
    // cancelled) leaves its remaining shots untracked.
    return (
      <Button
        size={CHIP_SIZE}
        width={CHIP_WIDTH}
        minWidth="0"
        variant="subtle"
        colorPalette="gray"
        disabled
        title={runFinished ? "Not tracked" : "Waiting to be tracked"}
      >
        {shot.shot_number}
      </Button>
    );
  }
  if (shot.status === "failed") {
    return (
      <Button
        size={CHIP_SIZE}
        width={CHIP_WIDTH}
        minWidth="0"
        variant="outline"
        colorPalette="red"
        disabled
        title="Tracking this shot failed"
      >
        {shot.shot_number} ✕
      </Button>
    );
  }
  return (
    <Button
      size={CHIP_SIZE}
      width={CHIP_WIDTH}
      minWidth="0"
      colorPalette={shot.color}
      variant={selected ? "solid" : "subtle"}
      title={`${shot.color} · ${formatVideoTime(shot.start_seconds)} · ${formatSplitTimes(shot)}`}
      onClick={onClick}
    >
      {shot.shot_number}
    </Button>
  );
};

// An end's name in the dropdown: its number and direction
const endOptionLabel = (end) => `End ${end.end_number} ${DIRECTION_LABELS[end.direction]}`;

// The ends of one draw, and the shots of the picked end
const DrawShots = ({ gameId, selectedShotId, onShotSelect }) => {
  // The end picked in the dropdown. The selected shot's end takes its place, so moving to a shot in another end
  // (e.g. with Next shot) shows that end.
  const [pickedEndId, setPickedEndId] = useState(null);
  const {
    data: game,
    error,
    isLoading,
  } = useQuery({
    queryKey: ["game", gameId],
    queryFn: () => fetchJson(`/api/games/${gameId}`),
    refetchInterval: (query) =>
      query.state.data && isFinished(query.state.data.run_status) ? false : POLL_INTERVAL_MS,
  });

  if (isLoading) {
    return <Spinner />;
  }
  if (error) {
    return <Text color="fg.error">Failed to load the draw: {error.message}</Text>;
  }

  const shotEnd = game.ends.find((option) => option.shots.some((shot) => shot.shot_id === selectedShotId));
  const end = shotEnd ?? game.ends.find((option) => option.end_id === pickedEndId) ?? game.ends[0];

  // Picking another end shows its first tracked shot, without scrolling away from the end's shots
  const onEndSelect = (endId) => {
    setPickedEndId(endId);
    const firstShot = game.ends.find((option) => option.end_id === endId)?.shots.find((shot) => shot.status === "tracked");
    onShotSelect(firstShot?.shot_id ?? null, { scroll: false });
  };

  return (
    <VStack align="stretch" gap="2">
      <HStack gap="3" wrap="wrap">
        <Text color="fg.muted">
          {formatVideoTime(game.start_seconds)} – {formatVideoTime(game.end_seconds)} · {game.ends.length} ends
        </Text>
        <VideoLink url={game.url} seconds={game.start_seconds}>
          {game.video_title ?? "Watch on YouTube"}
        </VideoLink>
      </HStack>
      {end && (
        <Stack direction={{ base: "column", lg: "row" }} align={{ base: "stretch", lg: "center" }} gap="3">
          <HStack gap="3" flexShrink="0">
            <NativeSelect.Root size="sm" width="auto">
              <NativeSelect.Field
                aria-label="End"
                value={end.end_id}
                onChange={(event) => onEndSelect(event.target.value)}
              >
                {game.ends.map((option) => (
                  <option key={option.end_id} value={option.end_id}>
                    {endOptionLabel(option)}
                  </option>
                ))}
              </NativeSelect.Field>
              <NativeSelect.Indicator />
            </NativeSelect.Root>
            {!end.complete && (
              <Badge colorPalette="red" title="An end has 16 shots, 8 of each color">
                {end.shots.length} shots
              </Badge>
            )}
          </HStack>
          <Grid templateColumns={CHIP_COLUMNS} gap="1" width={{ base: "100%", md: "fit-content" }}>
            {end.shots.map((shot) => (
              <ShotChip
                key={shot.shot_id}
                shot={shot}
                selected={shot.shot_id === selectedShotId}
                runFinished={isFinished(game.run_status)}
                onClick={() => onShotSelect(shot.shot_id)}
              />
            ))}
          </Grid>
        </Stack>
      )}
    </VStack>
  );
};

// How long (ms) after a shot is picked to keep scrolling to it while its content loads
const SCROLL_TO_PICK_MS = 3000;

// Scroll an element to the top of the screen. It's picked content that may still be loading (a spinner), and the
// page can't scroll it to the top until there's enough page below it, so scroll again whenever it changes size for
// a moment, i.e. once its content is shown.
const scrollIntoViewWhileLoading = (element) => {
  const observer = new ResizeObserver(() => element.scrollIntoView({ behavior: "smooth", block: "start" }));
  observer.observe(element);
  setTimeout(() => observer.disconnect(), SCROLL_TO_PICK_MS);
};

// A draw's name in the dropdown: when it was played, its number and its video, and how many of its shots are
// tracked until they all are
const drawOptionLabel = (game) => {
  const parts = [`Draw ${game.game_number}`, videoName(game)];
  if (formatDrawStart(game)) {
    parts.unshift(formatDrawStart(game));
  }
  if (game.num_tracked_shots < game.num_shots) {
    parts.push(`${game.num_tracked_shots} / ${game.num_shots} shots tracked`);
  }
  return parts.join(" · ");
};

// When a draw started (s since the epoch), or null if the video's date isn't known
const drawStartTime = (game) => {
  if (game.video_start_timestamp != null) {
    return game.video_start_timestamp + game.start_seconds;
  }
  if (game.video_date) {
    return Date.parse(`${game.video_date}T00:00`) / 1000 + game.start_seconds;
  }
  return null;
};

// The local day a draw started on, as a number that sorts by date (e.g. 20261111)
const drawDay = (start) => {
  const date = new Date(start * 1000);
  return date.getFullYear() * 10000 + (date.getMonth() + 1) * 100 + date.getDate();
};

// The draws by the day they were played, the most recent day first, and within a day in the order they were
// played. Draws whose date isn't known go last, in the order they came.
const sortByPlayed = (games) =>
  [...games].sort((a, b) => {
    const aStart = drawStartTime(a);
    const bStart = drawStartTime(b);
    if (aStart === null || bStart === null) {
      return (aStart === null) - (bStart === null);
    }
    return drawDay(bStart) - drawDay(aStart) || aStart - bStart;
  });

// A dropdown of the draws
const DrawSelect = ({ games, selectedGameId, onGameSelect }) => (
  <NativeSelect.Root size="md" width={{ base: "100%", md: "auto" }} maxWidth="100%">
    <NativeSelect.Field
      aria-label="Draw"
      value={selectedGameId}
      onChange={(event) => onGameSelect(event.target.value)}
    >
      {games.map((game) => (
        <option key={game.game_id} value={game.game_id}>
          {drawOptionLabel(game)}
        </option>
      ))}
    </NativeSelect.Field>
    <NativeSelect.Indicator />
  </NativeSelect.Root>
);

// Every draw found in the tracked videos, with the shots of the selected one
const Draws = () => {
  const isPhone = useIsPhone();
  const [selectedGameId, setSelectedGameId] = useState(loadSelectedGame);
  const [selectedShotId, setSelectedShotId] = useState(null);
  const shotViewerRef = useRef(null);
  // What to scroll to once it's shown, after the user picks a shot
  const scrollTargetRef = useRef(null);

  ///////////////
  //Use Functions
  ///////////////

  // Draws appear once a run's video is scanned, so they're checked while any run is in progress
  const { data: runs } = useQuery(trackingRunsQuery);
  const anyRunInProgress = runs?.some((run) => !isFinished(run.status)) ?? false;
  const { data: unsortedGames, error: gamesError } = useQuery({
    queryKey: ["games"],
    queryFn: () => fetchJson("/api/games"),
    refetchInterval: anyRunInProgress ? POLL_INTERVAL_MS : false,
  });
  const games = useMemo(() => unsortedGames && sortByPlayed(unsortedGames), [unsortedGames]);

  // On a phone the picked shot is shown below the draw's shots, so scroll to it
  useEffect(() => {
    const target = scrollTargetRef.current?.current;
    if (target) {
      scrollIntoViewWhileLoading(target);
      scrollTargetRef.current = null;
    }
  });

  ///////////
  //Callbacks
  ///////////

  const onGameSelect = (gameId) => {
    setSelectedGameId(gameId);
    setSelectedShotId(null);
    saveSelectedGame(gameId);
  };

  const onShotSelect = (shotId, { scroll = true } = {}) => {
    setSelectedShotId(shotId);
    scrollTargetRef.current = isPhone && scroll ? shotViewerRef : null;
  };

  // The draw picked before if it's still there, otherwise the first of the most recent day
  const selectedGame = games?.find((game) => game.game_id === selectedGameId) ?? games?.[0];

  return (
    <VStack align="stretch" gap="3" width="100%">
      {gamesError && <Text color="fg.error">Failed to load draws: {gamesError.message}</Text>}
      {games?.length === 0 && <Text color="fg.muted">No draws have been found yet.</Text>}
      {selectedGame && (
        <VStack align="stretch" gap="2">
          <HStack gap="3" wrap="wrap">
            <DrawSelect games={games} selectedGameId={selectedGame.game_id} onGameSelect={onGameSelect} />
            {!isFinished(selectedGame.run_status) && (
              <Badge colorPalette={STATUS_COLORS[selectedGame.run_status]}>{selectedGame.run_status}</Badge>
            )}
          </HStack>
          <DrawShots
            key={selectedGame.game_id}
            gameId={selectedGame.game_id}
            selectedShotId={selectedShotId}
            onShotSelect={onShotSelect}
          />
        </VStack>
      )}

      {selectedGame && selectedShotId && (
        <Box ref={shotViewerRef} scrollMarginTop="2" borderTopWidth="1px" pt="3">
          <ShotViewer shotId={selectedShotId} onShotChange={setSelectedShotId} />
        </Box>
      )}
    </VStack>
  );
};

export default Draws;
