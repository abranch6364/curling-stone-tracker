import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Badge, Box, Button, HStack, Heading, Spinner, Table, Text, VStack } from "@chakra-ui/react";

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

const SELECTED_GAME_STORAGE_KEY = "fullVideoTracking.selectedGameId";
const DIRECTION_LABELS = { to_away: "→ away", to_home: "← home" };

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
        size="xs"
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
      <Button size="xs" variant="outline" colorPalette="red" disabled title="Tracking this shot failed">
        {shot.shot_number} ✕
      </Button>
    );
  }
  return (
    <Button
      size="xs"
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
    refetchInterval: (query) => (query.state.data && isFinished(query.state.data.run_status) ? false : POLL_INTERVAL_MS),
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
          <HStack gap="1" wrap="wrap">
            {end.shots.map((shot) => (
              <ShotChip
                key={shot.shot_id}
                shot={shot}
                selected={shot.shot_id === selectedShotId}
                runFinished={isFinished(game.run_status)}
                onClick={() => onShotSelect(shot.shot_id)}
              />
            ))}
          </HStack>
        </HStack>
      ))}
    </VStack>
  );
};

// Every draw found in the tracked videos, with the shots of the selected one
const Draws = () => {
  const [selectedGameId, setSelectedGameId] = useState(loadSelectedGame);
  const [selectedShotId, setSelectedShotId] = useState(null);

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

  ///////////
  //Callbacks
  ///////////

  const onGameSelect = (gameId) => {
    setSelectedGameId(gameId);
    setSelectedShotId(null);
    saveSelectedGame(gameId);
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
          <Table.Root size="sm" interactive>
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
        )}
      </VStack>

      {selectedGameExists && (
        <DrawShots gameId={selectedGameId} selectedShotId={selectedShotId} onShotSelect={setSelectedShotId} />
      )}

      {selectedGameExists && selectedShotId && (
        <Box borderTopWidth="1px" pt="5">
          <ShotViewer shotId={selectedShotId} onShotChange={setSelectedShotId} />
        </Box>
      )}
    </VStack>
  );
};

export default Draws;
