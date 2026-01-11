import { useState } from "react";
import { useQueryClient, useMutation } from "@tanstack/react-query";
import {
  Button,
  HStack,
  VStack,
  Heading,
  RadioGroup,
  Box,
  Input,
  Select,
  Portal,
  createListCollection,
} from "@chakra-ui/react";

import CurlingSheetPlot from "../CurlingSheetPlot/CurlingSheetPlot";
import AnimationSlider from "../AnimationSlider/AnimationSlider";
import FetchDropdown from "../FetchDropdown/FetchDropdown";
import TimeInput from "../TimeInput/TimeInput";
import ImageViewer from "../ImageViewer/ImageViewer";

import { toIntPercent, findInsertionPoint, getStoneMinTime, getStoneMaxTime } from "../../utility/CurlingStoneHelper";

const VideoDetect = () => {
  const [setupId, setSetupId] = useState("");
  const [sheetSide, setSheetSide] = useState("away");

  const [videoLink, setVideoLink] = useState("");
  const [startTime, setStartTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [stones, setStones] = useState([]);

  const [detectionTimes, setDetectionTimes] = useState(null);
  const [detections, setDetections] = useState(null);

  const [imageDimensions, setImageDimensions] = useState(null);

  const [sliderTime, setSliderTime] = useState(0);
  const [selectedCameraView, setSelectedCameraView] = useState(null);

  const queryClient = useQueryClient();

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

  const getDetectionsIndexForTime = (time) => {
    if (!detectionTimes) {
      return 0;
    }
    return Math.max(findInsertionPoint(detectionTimes, time) - 1, 0);
  };

  ///////////////
  //Use Functions
  ///////////////

  const mutation = useMutation({
    mutationFn: requestVideoTracking,
    onSuccess: (data) => {
      queryClient.invalidateQueries({
        queryKey: ["/api/video_tracking_headers"],
      });
      setStones(data.state.stones);
      setDetectionTimes(data.mosaic_detection_times);
      setDetections(data.mosaic_detections);
    },
  });

  ///////////
  //Callbacks
  ///////////
  const onTrackingRequestClick = () => {
    mutation.mutate({ url: videoLink, start_seconds: startTime, duration: duration, setup_id: setupId });
  };

  const selectImage = () => {
    if (detectionTimes && detections) {
      const timeIndex = Math.max(findInsertionPoint(detectionTimes, sliderTime) - 1, 0);
      if (timeIndex >= 0 && timeIndex < detections.length) {
        return detections[timeIndex].images[selectedCameraView];
      }
    }

    return "";
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

      <VStack>
        <Heading as="h3" size="md">
          Camera Views
        </Heading>

        <Select.Root
          value={selectedCameraView ? [selectedCameraView] : []}
          collection={createListCollection({
            items: detections ? Object.keys(detections[getDetectionsIndexForTime(sliderTime)].images) : [],
          })}
          size="sm"
          width="320px"
          onValueChange={(details) => setSelectedCameraView(details.value[0])}
        >
          <Select.Control>
            <Select.Trigger>
              <Select.ValueText placeholder="Select Camera View" />
            </Select.Trigger>
          </Select.Control>
          <Portal>
            <Select.Positioner>
              <Select.Content>
                {detections &&
                  Object.keys(detections[getDetectionsIndexForTime(sliderTime)].images).map((key) => (
                    <Select.Item item={key} key={key}>
                      {key}
                      <Select.ItemIndicator />
                    </Select.Item>
                  ))}
              </Select.Content>
            </Select.Positioner>
          </Portal>
        </Select.Root>

        <Box position="relative">
          {detections &&
            imageDimensions &&
            selectedCameraView &&
            detections[getDetectionsIndexForTime(sliderTime)].detections[selectedCameraView].map((detection) => (
              <Box
                position="absolute"
                left={toIntPercent(detection.image_coordinates[0], imageDimensions.width) + "%"}
                top={toIntPercent(detection.image_coordinates[1], imageDimensions.height) + "%"}
                width={toIntPercent(detection.image_coordinates[2], imageDimensions.width) + "%"}
                height={toIntPercent(detection.image_coordinates[3], imageDimensions.height) + "%"}
                border={"1px solid " + detection.color}
                opacity="1"
                pointerEvents="none"
                zLevel="1000"
              ></Box>
            ))}
          {detections && (
            <ImageViewer
              file={selectImage()}
              includeLoadButton={false}
              onImageDimensionChange={setImageDimensions}
              encodingType="data:image/png;base64,"
            ></ImageViewer>
          )}
        </Box>
      </VStack>
    </HStack>
  );
};

export default VideoDetect;
