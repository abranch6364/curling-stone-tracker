import { useEffect, useState } from "react";
import { VStack, Heading, Box, Select, Portal, createListCollection } from "@chakra-ui/react";

import ImageViewer from "../ImageViewer/ImageViewer";

import { toIntPercent, findInsertionPoint } from "../../utility/CurlingStoneHelper";

const DetectionViewer = ({ selectedTime, detections, detectionTimes, onImageChange }) => {
  const [imageDimensions, setImageDimensions] = useState(null);
  const [selectedCameraView, setSelectedCameraView] = useState(null);

  //////////////////
  //Helper Functions
  //////////////////

  const getDetectionsIndexForTime = (time) => {
    if (!detectionTimes) {
      return 0;
    }
    return Math.max(findInsertionPoint(detectionTimes, time) - 1, 0);
  };

  ///////////////
  //Use Functions
  ///////////////

  useEffect(() => {
    onImageChange(selectImage());
  }, [selectedTime, detections, selectedCameraView]);

  ///////////
  //Callbacks
  ///////////

  const selectImage = () => {
    if (detectionTimes && detections) {
      const timeIndex = Math.max(findInsertionPoint(detectionTimes, selectedTime) - 1, 0);
      if (timeIndex >= 0 && timeIndex < detections.length) {
        return detections[timeIndex].images[selectedCameraView];
      }
    }

    return "";
  };

  return (
    <VStack>
      <Heading as="h3" size="md">
        Camera Views
      </Heading>

      <Select.Root
        value={selectedCameraView ? [selectedCameraView] : []}
        collection={createListCollection({
          items: detections ? Object.keys(detections[getDetectionsIndexForTime(selectedTime)].images) : [],
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
                Object.keys(detections[getDetectionsIndexForTime(selectedTime)].images).map((key) => (
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
          detections[getDetectionsIndexForTime(selectedTime)].detections[selectedCameraView].map((detection) => (
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
  );
};

export default DetectionViewer;
