import { useEffect, useState } from "react";
import { VStack, HStack, Heading, Box, Text } from "@chakra-ui/react";

import { toIntPercent, findInsertionPoint } from "../../utility/CurlingStoneHelper";

// A camera image scaled to a fixed height, with its stone detections drawn as boxes on top
const CameraImage = ({ image, detections, height, selected, onClick }) => {
  const [naturalSize, setNaturalSize] = useState(null);

  return (
    <Box
      position="relative"
      display="inline-block"
      height={height}
      cursor={onClick ? "pointer" : undefined}
      outline={selected ? "3px solid" : undefined}
      outlineColor="blue.solid"
      borderRadius="sm"
      onClick={onClick}
    >
      <img
        src={`data:image/png;base64,${image}`}
        alt="Camera view"
        style={{ height: "100%", display: "block" }}
        onLoad={(e) => setNaturalSize({ width: e.target.naturalWidth, height: e.target.naturalHeight })}
      />
      {naturalSize &&
        detections.map((detection, index) => (
          <Box
            key={index}
            position="absolute"
            left={toIntPercent(detection.image_coordinates[0], naturalSize.width) + "%"}
            top={toIntPercent(detection.image_coordinates[1], naturalSize.height) + "%"}
            width={toIntPercent(detection.image_coordinates[2], naturalSize.width) + "%"}
            height={toIntPercent(detection.image_coordinates[3], naturalSize.height) + "%"}
            border={"2px solid " + detection.color}
            pointerEvents="none"
          />
        ))}
    </Box>
  );
};

const DetectionViewer = ({ selectedTime, detections, detectionTimes, onImageChange, children }) => {
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

  const currentDetections = detections ? detections[getDetectionsIndexForTime(selectedTime)] : null;
  const cameraNames = currentDetections ? Object.keys(currentDetections.images) : [];

  ///////////////
  //Use Functions
  ///////////////

  // Select the first camera once results arrive
  useEffect(() => {
    if (cameraNames.length > 0 && !cameraNames.includes(selectedCameraView)) {
      setSelectedCameraView(cameraNames[0]);
    }
  }, [detections]);

  useEffect(() => {
    onImageChange(currentDetections && selectedCameraView ? currentDetections.images[selectedCameraView] : "");
  }, [selectedTime, detections, selectedCameraView]);

  return (
    <VStack align="start" gap="3" width="100%">
      <Heading as="h3" size="md">
        Camera Views
      </Heading>

      {!currentDetections && <Text color="fg.muted">Run video tracking to see the camera views.</Text>}

      <HStack wrap="wrap" align="start" gap="3">
        {cameraNames.map((name) => (
          <VStack key={name} align="start" gap="1">
            <Text fontSize="sm" fontWeight={name === selectedCameraView ? "bold" : "normal"}>
              {name}
            </Text>
            <CameraImage
              image={currentDetections.images[name]}
              detections={currentDetections.detections[name]}
              height="120px"
              selected={name === selectedCameraView}
              onClick={() => setSelectedCameraView(name)}
            />
          </VStack>
        ))}
      </HStack>

      {currentDetections && selectedCameraView && currentDetections.images[selectedCameraView] && (
        <HStack align="start" gap="6">
          <CameraImage
            image={currentDetections.images[selectedCameraView]}
            detections={currentDetections.detections[selectedCameraView]}
            height="480px"
          />
          <VStack align="start" gap="3">
            {children}
          </VStack>
        </HStack>
      )}
    </VStack>
  );
};

export default DetectionViewer;
