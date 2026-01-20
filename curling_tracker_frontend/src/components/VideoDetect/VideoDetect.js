import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Text, Button, HStack, VStack, Heading, RadioGroup, Input } from "@chakra-ui/react";

import CurlingSheetPlot from "../CurlingSheetPlot/CurlingSheetPlot";
import AnimationSlider from "../AnimationSlider/AnimationSlider";
import FetchDropdown from "../FetchDropdown/FetchDropdown";
import TimeInput from "../TimeInput/TimeInput";
import DetectionViewer from "../DetectionViewer/DetectionViewer";

import { base64ToFile, getStoneMinTime, getStoneMaxTime } from "../../utility/CurlingStoneHelper";

const VideoDetect = () => {
  const [setupId, setSetupId] = useState("");
  const [sheetSide, setSheetSide] = useState("away");

  const [videoLink, setVideoLink] = useState("");
  const [startTime, setStartTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [stones, setStones] = useState([]);

  const [detectionTimes, setDetectionTimes] = useState(null);
  const [detections, setDetections] = useState(null);

  const [sliderTime, setSliderTime] = useState(0);
  const [selectedDataset, setSelectedDataset] = useState(null);

  const [base64Image, setBase64Image] = useState(null);
  const [addToDatasetResultMessage, setAddToDatasetResultMessage] = useState("");

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
    return response.json();
  };

  const addImageToDataset = async ({ image_file, dataset_name }) => {
    const formData = new FormData();
    formData.append("file", image_file);
    formData.append("dataset_name", dataset_name);

    console.log("Adding to dataset:", dataset_name);
    const response = await fetch("/api/add_image_to_dataset", {
      method: "POST",
      body: formData,
    });

    return response.json();
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
    },
  });

  const addToDatasetMutation = useMutation({
    mutationFn: addImageToDataset,
    onSettled: (data) => {
      setAddToDatasetResultMessage(data.message);
      setTimeout(() => setAddToDatasetResultMessage(""), 5000);
    },
  });

  ///////////
  //Callbacks
  ///////////
  const onTrackingRequestClick = () => {
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

  return (
    <HStack align="start">
      <VStack alignItems="start">
        <Heading as="h3" size="md">
          Select Camera Setup
        </Heading>
        <FetchDropdown
          api_url="/api/camera_setup_headers"
          placeholder="Select Camera Setup"
          jsonToList={(json) => json}
          itemToKey={(item) => item.setup_id}
          itemToString={(item) => item.setup_name}
          value={setupId}
          setValue={setSetupId}
        />

        <HStack>
          <Heading as="h3" size="md">
            Video URL
          </Heading>
          <Input value={videoLink} onChange={(e) => setVideoLink(e.target.value)} />
        </HStack>

        <HStack>
          <Heading as="h3" size="md">
            Start Time
          </Heading>
          <TimeInput onChangeTotalSeconds={setStartTime} />
        </HStack>

        <HStack>
          <Heading as="h3" size="md">
            Duration
          </Heading>
          <TimeInput onChangeTotalSeconds={setDuration} />
        </HStack>

        <Button onClick={onTrackingRequestClick}>Request Video Tracking</Button>
      </VStack>
      <VStack>
        <Heading as="h3" size="md">
          Sheet Side
        </Heading>
        <RadioGroup.Root defaultValue="away" value={sheetSide} onValueChange={(details) => setSheetSide(details.value)}>
          <HStack gap="6">
            {["home", "away"].map((item) => (
              <RadioGroup.Item key={item} value={item}>
                <RadioGroup.ItemHiddenInput />
                <RadioGroup.ItemIndicator />
                <RadioGroup.ItemText>{item}</RadioGroup.ItemText>
              </RadioGroup.Item>
            ))}
          </HStack>
        </RadioGroup.Root>

        <VStack>
          <CurlingSheetPlot
            plotTime={sliderTime}
            stones={stones}
            sheetPlotYExtent={sheetSide === "away" ? [35, 65] : [-65, -35]}
          />
          <AnimationSlider
            sliderTime={sliderTime}
            onSliderTimeChange={setSliderTime}
            sliderMin={getStoneMinTime(stones)}
            sliderMax={getStoneMaxTime(stones)}
          />
        </VStack>
      </VStack>

      <VStack alignItems="start">
        <DetectionViewer
          selectedTime={sliderTime}
          detections={detections}
          detectionTimes={detectionTimes}
          onImageChange={setBase64Image}
        />
        <FetchDropdown
          label="Select Dataset To Add To"
          api_url="/api/dataset_headers"
          placeholder="Select Dataset"
          jsonToList={(json) => json}
          itemToKey={(item) => item.name}
          itemToString={(item) => item.name}
          value={selectedDataset}
          setValue={setSelectedDataset}
        />
        <Button onClick={onAddToDatasetClick}>Add Image To Dataset</Button>
        <Text color="fg.muted">{`${addToDatasetResultMessage}`}</Text>
      </VStack>
    </HStack>
  );
};

export default VideoDetect;
