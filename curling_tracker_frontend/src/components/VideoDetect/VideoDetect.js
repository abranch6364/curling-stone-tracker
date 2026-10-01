import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Text, Button, Box, HStack, VStack, Heading, Input, Field, SegmentGroup } from "@chakra-ui/react";

import CurlingSheetPlot from "../CurlingSheetPlot/CurlingSheetPlot";
import AnimationSlider from "../AnimationSlider/AnimationSlider";
import FetchDropdown from "../FetchDropdown/FetchDropdown";
import TimeInput from "../TimeInput/TimeInput";
import DetectionViewer from "../DetectionViewer/DetectionViewer";
import { toaster } from "../ui/toaster";

import { base64ToFile, getStoneMinTime, getStoneMaxTime } from "../../utility/CurlingStoneHelper";

const LAST_REQUEST_STORAGE_KEY = "videoDetect.lastRequest";

// The part of the sheet shown for each zoom level, as [min, max] y in feet
const SHEET_ZOOM_EXTENTS = {
  full: [-65, 65],
  home: [-65, -20],
  away: [20, 65],
};

const loadLastRequest = () => {
  try {
    return JSON.parse(localStorage.getItem(LAST_REQUEST_STORAGE_KEY)) ?? {};
  } catch {
    return {};
  }
};

const saveLastRequest = (request) => {
  try {
    localStorage.setItem(LAST_REQUEST_STORAGE_KEY, JSON.stringify(request));
  } catch {
    // Remembering the inputs is only a convenience
  }
};

const formatElapsed = (seconds) => `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;

const VideoDetect = () => {
  const [lastRequest] = useState(loadLastRequest);
  const [setupId, setSetupId] = useState(lastRequest.setupId ?? "");
  const [sheetZoom, setSheetZoom] = useState("full");

  const [videoLink, setVideoLink] = useState(lastRequest.videoLink ?? "");
  const [startTime, setStartTime] = useState(lastRequest.startTime ?? 0);
  const [duration, setDuration] = useState(lastRequest.duration ?? 0);
  const [stones, setStones] = useState([]);

  const [detectionTimes, setDetectionTimes] = useState(null);
  const [detections, setDetections] = useState(null);

  const [sliderTime, setSliderTime] = useState(0);
  const [selectedDataset, setSelectedDataset] = useState(null);

  const [base64Image, setBase64Image] = useState(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  //////////////////
  //Helper Functions
  //////////////////
  const requestVideoTracking = async (video_tracking_request) => {
    const response = await fetch("/api/request_video_tracking", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify(video_tracking_request),
    });
    const json = await response.json();
    if (!response.ok) {
      throw new Error(json.error || "Network response was not ok");
    }
    return json;
  };

  const addImageToDataset = async ({ image_file, dataset_name }) => {
    const formData = new FormData();
    formData.append("file", image_file);
    formData.append("dataset_name", dataset_name);

    const response = await fetch("/api/add_image_to_dataset", {
      method: "POST",
      body: formData,
    });
    const json = await response.json();
    if (!response.ok) {
      throw new Error(json.error || json.message || "Network response was not ok");
    }
    return json;
  };

  const stoneSummary = () => {
    const counts = {};
    for (const stone of stones) {
      counts[stone.color] = (counts[stone.color] ?? 0) + 1;
    }
    const colorCounts = Object.entries(counts)
      .map(([color, count]) => `${count} ${color}`)
      .join(", ");
    const timeRange = `${getStoneMinTime(stones).toFixed(1)}–${getStoneMaxTime(stones).toFixed(1)} s`;
    return `${stones.length} stones: ${colorCounts} · ${timeRange}`;
  };

  ///////////////
  //Use Functions
  ///////////////

  const requestVideoTrackingMutation = useMutation({
    mutationFn: requestVideoTracking,
    onSuccess: (data) => {
      setStones(data.state.stones);
      setDetectionTimes(data.mosaic_detection_times);
      setDetections(data.mosaic_detections);
      setSliderTime(getStoneMinTime(data.state.stones));
    },
    onError: (error) => {
      toaster.create({ type: "error", title: "Video tracking failed", description: error.message });
    },
  });

  const addToDatasetMutation = useMutation({
    mutationFn: addImageToDataset,
    onSuccess: (data) => {
      toaster.create({ type: "success", title: data.message ?? "Added image to dataset" });
    },
    onError: (error) => {
      toaster.create({ type: "error", title: "Failed to add image to dataset", description: error.message });
    },
  });

  const isTracking = requestVideoTrackingMutation.isPending;

  // Show how long the tracking request has been running
  useEffect(() => {
    if (!isTracking) {
      return;
    }
    const startedAt = Date.now();
    setElapsedSeconds(0);
    const interval = setInterval(() => setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000)), 1000);
    return () => clearInterval(interval);
  }, [isTracking]);

  ///////////
  //Callbacks
  ///////////
  const onTrackingRequestClick = () => {
    saveLastRequest({ setupId, videoLink, startTime, duration });
    requestVideoTrackingMutation.mutate({
      url: videoLink,
      start_seconds: startTime,
      duration: duration,
      setup_id: setupId,
    });
  };

  const onAddToDatasetClick = () => {
    if (!base64Image || !selectedDataset) {
      return;
    }

    addToDatasetMutation.mutate({
      image_file: base64ToFile(`data:image/png;base64,${base64Image}`, `frontend_detection.png`),
      dataset_name: selectedDataset,
    });
  };

  const canRequestTracking = setupId && videoLink.trim() !== "" && duration > 0;

  return (
    <VStack align="stretch" gap="5" width="100%">
      <VStack align="stretch" gap="2">
        <HStack justify="space-between">
          <Heading as="h3" size="md">
            Sheet
          </Heading>
          <SegmentGroup.Root size="sm" value={sheetZoom} onValueChange={(details) => setSheetZoom(details.value)}>
            <SegmentGroup.Indicator />
            <SegmentGroup.Items
              items={[
                { value: "full", label: "Full" },
                { value: "home", label: "Home" },
                { value: "away", label: "Away" },
              ]}
            />
          </SegmentGroup.Root>
        </HStack>
        <CurlingSheetPlot
          orientation="horizontal"
          plotTime={sliderTime}
          stones={stones}
          sheetPlotYExtent={SHEET_ZOOM_EXTENTS[sheetZoom]}
        />
        <AnimationSlider
          sliderTime={sliderTime}
          onSliderTimeChange={setSliderTime}
          sliderMin={getStoneMinTime(stones)}
          sliderMax={getStoneMaxTime(stones)}
        />
      </VStack>

      <VStack align="start" gap="2">
        <HStack wrap="wrap" align="end" gap="4" width="100%">
          <Field.Root width="auto">
            <Field.Label>Camera setup</Field.Label>
            <Box pointerEvents={isTracking ? "none" : undefined} opacity={isTracking ? 0.5 : 1}>
              <FetchDropdown
                api_url="/api/camera_setup_headers"
                placeholder="Select Camera Setup"
                jsonToList={(json) => json}
                itemToKey={(item) => item.setup_id}
                itemToString={(item) => item.setup_name}
                value={setupId}
                setValue={setSetupId}
              />
            </Box>
          </Field.Root>

          <Field.Root flex="1" minWidth="280px">
            <Field.Label>Video URL</Field.Label>
            <Input
              size="sm"
              placeholder="https://www.youtube.com/watch?v=..."
              value={videoLink}
              onChange={(e) => setVideoLink(e.target.value)}
              disabled={isTracking}
            />
          </Field.Root>

          {/* Not a Field: a Field gives all three of TimeInput's number inputs the same id */}
          <VStack align="start" gap="1.5">
            <Text textStyle="sm" fontWeight="medium">
              Start (h:m:s)
            </Text>
            <TimeInput onChangeTotalSeconds={setStartTime} initialSeconds={startTime} disabled={isTracking} />
          </VStack>

          <VStack align="start" gap="1.5">
            <Text textStyle="sm" fontWeight="medium">
              Duration (h:m:s)
            </Text>
            <TimeInput onChangeTotalSeconds={setDuration} initialSeconds={duration} disabled={isTracking} />
          </VStack>

          <Button
            onClick={onTrackingRequestClick}
            loading={isTracking}
            loadingText="Tracking…"
            disabled={!canRequestTracking}
          >
            Track Video
          </Button>
        </HStack>

        {isTracking && (
          <Text color="fg.muted">
            Downloading and tracking the video… {formatElapsed(elapsedSeconds)} elapsed. This usually takes a minute
            or two.
          </Text>
        )}
        {!isTracking && stones.length > 0 && <Text fontWeight="medium">{stoneSummary()}</Text>}
      </VStack>

      <DetectionViewer
        selectedTime={sliderTime}
        detections={detections}
        detectionTimes={detectionTimes}
        onImageChange={setBase64Image}
      >
        <FetchDropdown
          label="Add this image to a dataset"
          api_url="/api/dataset_headers"
          placeholder="Select Dataset"
          jsonToList={(json) => json}
          itemToKey={(item) => item.name}
          itemToString={(item) => item.name}
          value={selectedDataset}
          setValue={setSelectedDataset}
        />
        <Button
          size="sm"
          onClick={onAddToDatasetClick}
          disabled={!base64Image || !selectedDataset}
          loading={addToDatasetMutation.isPending}
        >
          Add Image To Dataset
        </Button>
      </DetectionViewer>
    </VStack>
  );
};

export default VideoDetect;
