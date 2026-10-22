import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge, Button, Field, HStack, Heading, Input, Progress, Table, Text, VStack } from "@chakra-ui/react";

import FetchDropdown from "../FetchDropdown/FetchDropdown";
import { toaster } from "../ui/toaster";

import {
  STATUS_COLORS,
  VideoLink,
  fetchJson,
  formatCreatedAt,
  isFinished,
  shortRunId,
  trackingRunsQuery,
  videoName,
} from "../../utility/TrackingRunHelper";

const RunProgress = ({ run }) => (
  <VStack align="stretch" gap="1" minWidth="220px">
    {!isFinished(run.status) && (
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

// Start tracking full videos and follow the runs' progress
const TrackVideos = () => {
  const queryClient = useQueryClient();
  const [setupId, setSetupId] = useState("");
  const [videoLink, setVideoLink] = useState("");

  ///////////////
  //Use Functions
  ///////////////

  const { data: runs, error: runsError } = useQuery(trackingRunsQuery);

  const startRunMutation = useMutation({
    mutationFn: (request) =>
      fetchJson("/api/tracking_runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      }),
    onSuccess: () => {
      toaster.create({
        type: "success",
        title: "Tracking started",
        description: "The video is processed in the background. Its draws appear in the Draws tab once it is scanned.",
      });
      setVideoLink("");
      queryClient.invalidateQueries({ queryKey: ["tracking_runs"] });
    },
    onError: (error) => {
      toaster.create({ type: "error", title: "Failed to start tracking", description: error.message });
    },
  });

  const cancelRunMutation = useMutation({
    mutationFn: (runId) => fetchJson(`/api/tracking_runs/${runId}/cancel`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tracking_runs"] });
      queryClient.invalidateQueries({ queryKey: ["games"] });
      queryClient.invalidateQueries({ queryKey: ["game"] });
    },
    onError: (error) => {
      toaster.create({ type: "error", title: "Failed to cancel the run", description: error.message });
    },
  });

  ///////////
  //Callbacks
  ///////////

  const onCancelClick = (run) => {
    if (window.confirm("Cancel this run? Its progress is lost and it can't be resumed.")) {
      cancelRunMutation.mutate(run.run_id);
    }
  };

  const canStart = setupId && videoLink.trim() !== "" && !startRunMutation.isPending;

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
          <Table.Root size="sm">
            <Table.Header>
              <Table.Row>
                <Table.ColumnHeader>Video</Table.ColumnHeader>
                <Table.ColumnHeader>Run</Table.ColumnHeader>
                <Table.ColumnHeader>Camera setup</Table.ColumnHeader>
                <Table.ColumnHeader>Status</Table.ColumnHeader>
                <Table.ColumnHeader>Progress</Table.ColumnHeader>
                <Table.ColumnHeader />
              </Table.Row>
            </Table.Header>
            <Table.Body>
              {runs.map((run) => (
                <Table.Row key={run.run_id}>
                  <Table.Cell maxWidth="320px" truncate>
                    <VideoLink url={run.url} seconds={0}>
                      {videoName(run)}
                    </VideoLink>
                  </Table.Cell>
                  <Table.Cell title={run.run_id}>
                    {shortRunId(run.run_id)} · {formatCreatedAt(run.created_at)}
                  </Table.Cell>
                  <Table.Cell>{run.setup_name}</Table.Cell>
                  <Table.Cell>
                    <Badge colorPalette={STATUS_COLORS[run.status]}>{run.status}</Badge>
                  </Table.Cell>
                  <Table.Cell>
                    <RunProgress run={run} />
                  </Table.Cell>
                  <Table.Cell>
                    {!isFinished(run.status) && (
                      <Button
                        size="xs"
                        variant="outline"
                        colorPalette="red"
                        loading={cancelRunMutation.isPending && cancelRunMutation.variables === run.run_id}
                        onClick={() => onCancelClick(run)}
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
    </VStack>
  );
};

export default TrackVideos;
