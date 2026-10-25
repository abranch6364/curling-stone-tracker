import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Badge, Box, Button, Grid, HStack, Heading, Spinner, Table, Text, VStack } from "@chakra-ui/react";

import ShotViewer from "../ShotViewer/ShotViewer";

import {
  POLL_INTERVAL_MS,
  STATUS_COLORS,
  VideoLink,
  fetchJson,
  formatCreatedAt,
  formatDrawStart,
  formatSplitTimes,
  formatVideoTime,
  isFinished,
  shortRunId,
  trackingRunsQuery,
  videoName,
} from "../../utility/TrackingRunHelper";
import useIsPhone from "../../utility/useIsPhone";

const SELECTED_GAME_STORAGE_KEY = "fullVideoTracking.selectedGameId";
const DIRECTION_LABELS = { to_away: "→ away", to_home: "← home" };
// Shot chips are bigger on a phone, to be easier to tap
const CHIP_SIZE = { base: "sm", md: "xs" };
// At most this many shot chips per line, so an end's 16 shots are two lines of 8
const CHIPS_PER_LINE = 8;
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

// The ends and shots of one draw
const DrawShots = ({ gameId, selectedShotId, onShotSelect }) => {
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

  return (
    <VStack align="stretch" gap="2">
      <HStack gap="3" wrap="wrap">
        <Heading as="h3" size="md">
          Draw {game.game_number}
          {formatDrawStart(game) && (
            <Text as="span" fontWeight="normal" ms="3">
              {formatDrawStart(game)}
            </Text>
          )}
        </Heading>
        <Text color="fg.muted">
          {formatVideoTime(game.start_seconds)} – {formatVideoTime(game.end_seconds)} · {game.ends.length} ends
        </Text>
        <VideoLink url={game.url} seconds={game.start_seconds}>
          {game.video_title ?? "Watch on YouTube"}
        </VideoLink>
      </HStack>
      {game.ends.map((end) => (
        <HStack key={end.end_id} gap="3" wrap="wrap">
          <Text fontSize="sm" width="120px">
            End {end.end_number} {DIRECTION_LABELS[end.direction]}
          </Text>
          {!end.complete && (
            <Badge colorPalette="red" title="An end has 16 shots, 8 of each color">
              {end.shots.length} shots
            </Badge>
          )}
          <Grid
            templateColumns={{
              base: `repeat(${CHIPS_PER_LINE}, minmax(0, 1fr))`,
              md: `repeat(${CHIPS_PER_LINE}, auto)`,
            }}
            gap="1"
            width={{ base: "100%", md: "auto" }}
          >
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
        </HStack>
      ))}
    </VStack>
  );
};

// How long (ms) after a draw or shot is picked to keep scrolling to it while its content loads
const SCROLL_TO_PICK_MS = 3000;

// Scroll an element to the top of the screen. It's picked content that may still be loading (a spinner), and the
// page can't scroll it to the top until there's enough page below it, so scroll again whenever it changes size for
// a moment, i.e. once its content is shown.
const scrollIntoViewWhileLoading = (element) => {
  const observer = new ResizeObserver(() => element.scrollIntoView({ behavior: "smooth", block: "start" }));
  observer.observe(element);
  setTimeout(() => observer.disconnect(), SCROLL_TO_PICK_MS);
};

// The draws as a table, on wider screens
const DrawTable = ({ games, selectedGameId, onGameSelect }) => (
  <Table.Root size="sm" interactive hideBelow="md">
    <Table.Header>
      <Table.Row>
        <Table.ColumnHeader>Date</Table.ColumnHeader>
        <Table.ColumnHeader>Draw</Table.ColumnHeader>
        <Table.ColumnHeader>Video</Table.ColumnHeader>
        <Table.ColumnHeader>Run</Table.ColumnHeader>
        <Table.ColumnHeader>Time in video</Table.ColumnHeader>
        <Table.ColumnHeader>Ends</Table.ColumnHeader>
        <Table.ColumnHeader>Shots tracked</Table.ColumnHeader>
      </Table.Row>
    </Table.Header>
    <Table.Body>
      {games.map((game) => (
        <Table.Row
          key={game.game_id}
          cursor="pointer"
          bg={game.game_id === selectedGameId ? "bg.muted" : undefined}
          onClick={() => onGameSelect(game.game_id)}
        >
          <Table.Cell whiteSpace="nowrap">{formatDrawStart(game) ?? "—"}</Table.Cell>
          <Table.Cell fontWeight="medium">Draw {game.game_number}</Table.Cell>
          <Table.Cell maxWidth="360px" truncate>
            <VideoLink url={game.url} seconds={game.start_seconds}>
              {videoName(game)}
            </VideoLink>
          </Table.Cell>
          <Table.Cell title={game.run_id}>
            {shortRunId(game.run_id)} · {formatCreatedAt(game.run_created_at)}
            {!isFinished(game.run_status) && (
              <Badge ms="2" colorPalette={STATUS_COLORS[game.run_status]}>
                {game.run_status}
              </Badge>
            )}
          </Table.Cell>
          <Table.Cell>
            {formatVideoTime(game.start_seconds)} – {formatVideoTime(game.end_seconds)}
          </Table.Cell>
          <Table.Cell>{game.num_ends}</Table.Cell>
          <Table.Cell>
            {game.num_tracked_shots} / {game.num_shots}
          </Table.Cell>
        </Table.Row>
      ))}
    </Table.Body>
  </Table.Root>
);

// The draws as a list of cards, on a phone, with what matters there: when, which draw, the video and its shots
const DrawCards = ({ games, selectedGameId, onGameSelect }) => (
  <VStack align="stretch" gap="2" hideFrom="md">
    {games.map((game) => (
      <VStack
        key={game.game_id}
        align="stretch"
        gap="1"
        p="3"
        borderWidth="1px"
        borderRadius="md"
        cursor="pointer"
        bg={game.game_id === selectedGameId ? "bg.muted" : undefined}
        onClick={() => onGameSelect(game.game_id)}
      >
        <HStack justify="space-between" gap="2">
          <Text fontWeight="bold">Draw {game.game_number}</Text>
          <Text fontSize="sm" color="fg.muted">
            {game.num_tracked_shots} / {game.num_shots} shots
          </Text>
        </HStack>
        <HStack gap="2">
          <Text fontSize="sm">{formatDrawStart(game) ?? "—"}</Text>
          {!isFinished(game.run_status) && (
            <Badge colorPalette={STATUS_COLORS[game.run_status]}>{game.run_status}</Badge>
          )}
        </HStack>
        <Box fontSize="sm" minWidth="0">
          <VideoLink url={game.url} seconds={game.start_seconds}>
            {videoName(game)}
          </VideoLink>
        </Box>
      </VStack>
    ))}
  </VStack>
);

// Every draw found in the tracked videos, with the shots of the selected one
const Draws = () => {
  const isPhone = useIsPhone();
  const [selectedGameId, setSelectedGameId] = useState(loadSelectedGame);
  const [selectedShotId, setSelectedShotId] = useState(null);
  const drawShotsRef = useRef(null);
  const shotViewerRef = useRef(null);
  // What to scroll to once it's shown, after the user picks a draw or a shot
  const scrollTargetRef = useRef(null);

  ///////////////
  //Use Functions
  ///////////////

  // Draws appear once a run's video is scanned, so they're checked while any run is in progress
  const { data: runs } = useQuery(trackingRunsQuery);
  const anyRunInProgress = runs?.some((run) => !isFinished(run.status)) ?? false;
  const { data: games, error: gamesError } = useQuery({
    queryKey: ["games"],
    queryFn: () => fetchJson("/api/games"),
    refetchInterval: anyRunInProgress ? POLL_INTERVAL_MS : false,
  });

  // On a phone what was picked is shown below the list, so scroll to it. Not for the draw remembered from before,
  // only for what the user picks.
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
    scrollTargetRef.current = isPhone ? drawShotsRef : null;
  };

  const onShotSelect = (shotId) => {
    setSelectedShotId(shotId);
    scrollTargetRef.current = isPhone ? shotViewerRef : null;
  };

  const selectedGameExists = games?.some((game) => game.game_id === selectedGameId);

  return (
    <VStack align="stretch" gap="6" width="100%">
      <VStack align="stretch" gap="2">
        <Heading as="h3" size="md">
          Draws
        </Heading>
        {gamesError && <Text color="fg.error">Failed to load draws: {gamesError.message}</Text>}
        {games?.length === 0 && <Text color="fg.muted">No draws have been found yet.</Text>}
        {games?.length > 0 && (
          <>
            <DrawTable games={games} selectedGameId={selectedGameId} onGameSelect={onGameSelect} />
            <DrawCards games={games} selectedGameId={selectedGameId} onGameSelect={onGameSelect} />
          </>
        )}
      </VStack>

      {selectedGameExists && (
        <Box ref={drawShotsRef} scrollMarginTop="2">
          <DrawShots gameId={selectedGameId} selectedShotId={selectedShotId} onShotSelect={onShotSelect} />
        </Box>
      )}

      {selectedGameExists && selectedShotId && (
        <Box ref={shotViewerRef} scrollMarginTop="2" borderTopWidth="1px" pt="5">
          <ShotViewer shotId={selectedShotId} onShotChange={setSelectedShotId} />
        </Box>
      )}
    </VStack>
  );
};

export default Draws;
