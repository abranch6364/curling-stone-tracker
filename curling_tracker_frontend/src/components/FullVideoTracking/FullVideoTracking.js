import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Accordion,
  Badge,
  Box,
  Button,
  Field,
  HStack,
  Heading,
  Input,
  Progress,
  Spinner,
  Table,
  Text,
  VStack,
} from "@chakra-ui/react";

import FetchDropdown from "../FetchDropdown/FetchDropdown";
import ShotViewer from "../ShotViewer/ShotViewer";
import { toaster } from "../ui/toaster";

import { formatVideoTime } from "../../utility/CurlingStoneHelper";

const SELECTED_RUN_STORAGE_KEY = "fullVideoTracking.selectedRunId";
// How often (ms) unfinished runs are checked for progress
const POLL_INTERVAL_MS = 2000;

const FINISHED_STATUSES = ["complete", "failed", "cancelled"];
const STATUS_COLORS = {
  queued: "gray",
  downloading: "blue",
  scanning: "blue",
  tracking: "blue",
  complete: "green",
  failed: "red",
  cancelled: "orange",
};
const DIRECTION_LABELS = { to_away: "→ away", to_home: "← home" };

const isFinished = (run) => FINISHED_STATUSES.includes(run.status);

const loadSelectedRun = () => {
  try {
    return localStorage.getItem(SELECTED_RUN_STORAGE_KEY);
  } catch {
    return null;
  }
};

const saveSelectedRun = (runId) => {
  try {
    localStorage.setItem(SELECTED_RUN_STORAGE_KEY, runId);
  } catch {
    // Remembering the run is only a convenience
  }
};

// SQLite's CURRENT_TIMESTAMP is UTC without a zone
const formatCreatedAt = (createdAt) => new Date(createdAt.replace(" ", "T") + "Z").toLocaleString();

const fetchJson = async (url, options) => {
  const response = await fetch(url, options);
  const json = await response.json();
  if (!response.ok) {
    throw new Error(json.error || "Network response was not ok");
  }
  return json;
};

const RunProgress = ({ run }) => (
  <VStack align="stretch" gap="1" minWidth="220px">
    {!isFinished(run) && (
      <Progress.Root size="sm" value={Math.round(run.progress * 100)}>
        <Progress.Track>
          <Progress.Range />
        </Progress.Track>
      </Progress.Root>
    )}
    <Text fontSize="xs" color={run.status === "failed" ? "fg.error" : "fg.muted"}>
      {run.status === "failed" ? run.error : run.message}
    </Text>
  </VStack>
);

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
      title={`${shot.color} · ${formatVideoTime(shot.start_seconds)}`}
      onClick={onClick}
    >
      {shot.shot_number}
    </Button>
  );
};

// The games, ends and shots found in a run
const RunTree = ({ runId, selectedShotId, onShotSelect }) => {
  const {
    data: run,
    error,
    isLoading,
  } = useQuery({
    queryKey: ["tracking_run", runId],
    queryFn: () => fetchJson(`/api/tracking_runs/${runId}`),
    refetchInterval: (query) => (query.state.data && isFinished(query.state.data) ? false : POLL_INTERVAL_MS),
  });

  if (isLoading) {
    return <Spinner />;
  }
  if (error) {
    return <Text color="fg.error">Failed to load the run: {error.message}</Text>;
  }
  if (run.games.length === 0) {
    return (
      <Text color="fg.muted">
        {isFinished(run) ? "No games were found in this video." : "Games will appear here once the video is scanned."}
      </Text>
    );
  }

  return (
    <Accordion.Root multiple defaultValue={run.games.map((game) => game.game_id)}>
      {run.games.map((game) => (
        <Accordion.Item key={game.game_id} value={game.game_id}>
          <Accordion.ItemTrigger>
            <Text fontWeight="medium" flex="1">
              Game {game.game_number}
              <Text as="span" fontWeight="normal" color="fg.muted" ms="3">
                {formatVideoTime(game.start_seconds)} – {formatVideoTime(game.end_seconds)} · {game.ends.length} ends
              </Text>
            </Text>
            <Accordion.ItemIndicator />
          </Accordion.ItemTrigger>
          <Accordion.ItemContent>
            <Accordion.ItemBody>
              <VStack align="stretch" gap="2">
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
                          runFinished={isFinished(run)}
                          onClick={() => onShotSelect(shot.shot_id)}
                        />
                      ))}
                    </HStack>
                  </HStack>
                ))}
              </VStack>
            </Accordion.ItemBody>
          </Accordion.ItemContent>
        </Accordion.Item>
      ))}
    </Accordion.Root>
  );
};

const FullVideoTracking = () => {
  const queryClient = useQueryClient();
  const [setupId, setSetupId] = useState("");
  const [videoLink, setVideoLink] = useState("");
  const [selectedRunId, setSelectedRunId] = useState(loadSelectedRun);
  const [selectedShotId, setSelectedShotId] = useState(null);

  ///////////////
  //Use Functions
  ///////////////

  const { data: runs, error: runsError } = useQuery({
    queryKey: ["tracking_runs"],
    queryFn: () => fetchJson("/api/tracking_runs"),
    refetchInterval: (query) => (query.state.data?.some((run) => !isFinished(run)) ? POLL_INTERVAL_MS : false),
  });

  const startRunMutation = useMutation({
    mutationFn: (request) =>
      fetchJson("/api/tracking_runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      }),
    onSuccess: (data) => {
      toaster.create({
        type: "success",
        title: "Tracking started",
        description: "The video is processed in the background.",
      });
      setVideoLink("");
      onRunSelect(data.run_id);
      queryClient.invalidateQueries({ queryKey: ["tracking_runs"] });
    },
    onError: (error) => {
      toaster.create({ type: "error", title: "Failed to start tracking", description: error.message });
    },
  });

  const cancelRunMutation = useMutation({
    mutationFn: (runId) => fetchJson(`/api/tracking_runs/${runId}/cancel`, { method: "POST" }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["tracking_runs"] });
      queryClient.invalidateQueries({ queryKey: ["tracking_run", data.run_id] });
    },
    onError: (error) => {
      toaster.create({ type: "error", title: "Failed to cancel the run", description: error.message });
    },
  });

  ///////////
  //Callbacks
  ///////////

  const onCancelClick = (event, run) => {
    // Don't also select the run's row
    event.stopPropagation();
    if (window.confirm("Cancel this run? Its progress is lost and it can't be resumed.")) {
      cancelRunMutation.mutate(run.run_id);
    }
  };

  const onRunSelect = (runId) => {
    setSelectedRunId(runId);
    setSelectedShotId(null);
    saveSelectedRun(runId);
  };

  const canStart = setupId && videoLink.trim() !== "" && !startRunMutation.isPending;
  const selectedRunExists = runs?.some((run) => run.run_id === selectedRunId);

  return (
    <VStack align="stretch" gap="6" width="100%">
      <HStack wrap="wrap" align="end" gap="4">
        <Field.Root width="auto">
          <Field.Label>Camera setup</Field.Label>
          <FetchDropdown
            api_url="/api/camera_setup_headers"
            placeholder="Select Camera Setup"
            jsonToList={(json) => json}
            itemToKey={(item) => item.setup_id}
            itemToString={(item) => item.setup_name}
            value={setupId}
            setValue={setSetupId}
          />
        </Field.Root>
        <Field.Root flex="1" minWidth="280px">
          <Field.Label>Video URL</Field.Label>
          <Input
            size="sm"
            placeholder="https://www.youtube.com/watch?v=..."
            value={videoLink}
            onChange={(e) => setVideoLink(e.target.value)}
          />
        </Field.Root>
        <Button
          onClick={() => startRunMutation.mutate({ url: videoLink.trim(), setup_id: setupId })}
          disabled={!canStart}
          loading={startRunMutation.isPending}
        >
          Track Full Video
        </Button>
      </HStack>

      <VStack align="stretch" gap="2">
        <Heading as="h3" size="md">
          Runs
        </Heading>
        {runsError && <Text color="fg.error">Failed to load runs: {runsError.message}</Text>}
        {runs?.length === 0 && <Text color="fg.muted">No videos have been tracked yet.</Text>}
        {runs?.length > 0 && (
          <Table.Root size="sm" interactive>
            <Table.Header>
              <Table.Row>
                <Table.ColumnHeader>Video</Table.ColumnHeader>
                <Table.ColumnHeader>Camera setup</Table.ColumnHeader>
                <Table.ColumnHeader>Started</Table.ColumnHeader>
                <Table.ColumnHeader>Status</Table.ColumnHeader>
                <Table.ColumnHeader>Progress</Table.ColumnHeader>
                <Table.ColumnHeader />
              </Table.Row>
            </Table.Header>
            <Table.Body>
              {runs.map((run) => (
                <Table.Row
                  key={run.run_id}
                  cursor="pointer"
                  bg={run.run_id === selectedRunId ? "bg.muted" : undefined}
                  onClick={() => onRunSelect(run.run_id)}
                >
                  <Table.Cell maxWidth="320px" truncate title={run.url}>
                    {run.url}
                  </Table.Cell>
                  <Table.Cell>{run.setup_name}</Table.Cell>
                  <Table.Cell>{formatCreatedAt(run.created_at)}</Table.Cell>
                  <Table.Cell>
                    <Badge colorPalette={STATUS_COLORS[run.status]}>{run.status}</Badge>
                  </Table.Cell>
                  <Table.Cell>
                    <RunProgress run={run} />
                  </Table.Cell>
                  <Table.Cell>
                    {!isFinished(run) && (
                      <Button
                        size="xs"
                        variant="outline"
                        colorPalette="red"
                        loading={cancelRunMutation.isPending && cancelRunMutation.variables === run.run_id}
                        onClick={(event) => onCancelClick(event, run)}
                      >
                        Cancel
                      </Button>
                    )}
                  </Table.Cell>
                </Table.Row>
              ))}
            </Table.Body>
          </Table.Root>
        )}
      </VStack>

      {selectedRunExists && (
        <VStack align="stretch" gap="2">
          <Heading as="h3" size="md">
            Games
          </Heading>
          <RunTree runId={selectedRunId} selectedShotId={selectedShotId} onShotSelect={setSelectedShotId} />
        </VStack>
      )}

      {selectedRunExists && selectedShotId && (
        <Box borderTopWidth="1px" pt="5">
          <ShotViewer shotId={selectedShotId} onShotChange={setSelectedShotId} />
        </Box>
      )}
    </VStack>
  );
};

export default FullVideoTracking;
