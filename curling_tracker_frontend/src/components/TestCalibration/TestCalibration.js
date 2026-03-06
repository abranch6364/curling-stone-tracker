import { useState, useEffect, useRef } from "react";
import { useQueryClient, useQuery } from "@tanstack/react-query";
import { Button, Input, HStack, VStack, Text, Heading, FileUpload, Box, RadioGroup } from "@chakra-ui/react";

import ImageViewer from "../ImageViewer/ImageViewer";
import FetchDropdown from "../FetchDropdown/FetchDropdown";
import CurlingSheetPlot from "../CurlingSheetPlot/CurlingSheetPlot";

const fetchCameraSetup = async (setupId) => {
  const params = new URLSearchParams({ setup_id: setupId });
  const response = await fetch("/api/camera_setup?" + params, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });
  if (!response.ok) {
    throw new Error("Network response was not ok");
  }

  return response.json();
};

const fetchSheetCoordinates = async ({ camera_id, image_points }) => {
  const response = await fetch("/api/image_to_sheet_coordinates", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ camera_id: camera_id, image_points: image_points }),
  });

  if (!response.ok) {
    throw new Error("Network response was not ok");
  }

  return response.json();
};

const TestCalibration = ({ selectedSetupId, setSelectedSetupId }) => {
  const [fullImage, setFullImage] = useState(null);
  const [splitImages, setSplitImages] = useState(null);
  const [selectedCameraIndex, setSelectedCameraIndex] = useState(-1);

  const [imageCoords, setImageCoords] = useState([]);
  const [sheetSide, setSheetSide] = useState("away");

  const splitImageByCamera = (image) => {
    var imageElement = new Image();
    imageElement.onload = splitImage;
    imageElement.src = URL.createObjectURL(image);

    function splitImage() {
      var newSplitImages = {};
      for (const c of data.cameras) {
        var canvas = document.createElement("canvas");
        var xOrigin = Math.min(c.corner1[0], c.corner2[0]);
        var yOrigin = Math.min(c.corner1[1], c.corner2[1]);
        canvas.width = Math.abs(c.corner1[0] - c.corner2[0]);
        canvas.height = Math.abs(c.corner1[1] - c.corner2[1]);

        var context = canvas.getContext("2d");
        context.drawImage(
          imageElement,
          xOrigin,
          yOrigin,
          canvas.width,
          canvas.height,
          0,
          0,
          canvas.width,
          canvas.height,
        );
        newSplitImages[c.camera_id] = canvas.toDataURL();
      }
      setSplitImages(newSplitImages);
    }
  };

  ///////////////
  //Use Functions
  ///////////////
  const { data, error, isLoading } = useQuery({
    queryKey: ["/api/camera_setup", selectedSetupId],
    queryFn: () => fetchCameraSetup(selectedSetupId),
    initialData: null,
    enabled: selectedSetupId !== "",
    timeToStale: Infinity,
  });

  const {
    data: sheetCoordinatesData,
    error: sheetCoordinatesError,
    isLoading: sheetCoordinatesLoading,
  } = useQuery({
    queryKey: [imageCoords, selectedSetupId, selectedCameraIndex],
    queryFn: () =>
      fetchSheetCoordinates({ camera_id: data.cameras[selectedCameraIndex].camera_id, image_points: imageCoords }),
    initialData: [-100, -100],
    enabled: selectedSetupId !== "" && selectedCameraIndex !== -1,
    timeToStale: Infinity,
  });

  useEffect(() => {
    if (fullImage !== null && data !== null) {
      splitImageByCamera(fullImage);
    }
  }, [data]);

  ///////////////
  //Callbacks
  ///////////////

  const imageViewerClick = (x, y) => {
    setImageCoords([x, y]);
    console.log("Image clicked at: ", x, y);
  };

  const onImageFileChange = (details) => {
    setFullImage(details.acceptedFiles[0]);
    if (details.acceptedFiles[0] !== null && data !== null) {
      splitImageByCamera(details.acceptedFiles[0]);
    }
  };

  const onCameraButtonClick = (index) => {
    setSelectedCameraIndex(index);
  };

  const onDropdownChange = (value) => {
    setSelectedCameraIndex(-1);
    setSelectedSetupId(value);
  };

  return (
    <HStack alignItems="start">
      <VStack alignItems="start" spacing="10px" marginRight="20px">
        <Heading size="md">Selected Camera Setup</Heading>
        <FetchDropdown
          api_url="/api/camera_setup_headers"
          placeholder="Select Camera Setup"
          jsonToList={(json) => json}
          itemToKey={(item) => item.setup_id}
          itemToString={(item) => item.setup_name}
          value={selectedSetupId}
          setValue={onDropdownChange}
        />

        <Text>Cameras</Text>
        {data &&
          data.cameras.map((camera, index) => (
            <Button
              key={index}
              width="200px"
              justifyContent="flex-start"
              onClick={() => onCameraButtonClick(index)}
              variant={selectedCameraIndex === index ? "solid" : "outline"}
            >
              {camera.camera_name}
            </Button>
          ))}
      </VStack>
      <VStack>
        <ImageViewer
          onImageClick={imageViewerClick}
          file={
            selectedCameraIndex !== -1 && splitImages !== null && data
              ? splitImages[data.cameras[selectedCameraIndex].camera_id]
              : null
          }
        />
        <FileUpload.Root onFileChange={(details) => onImageFileChange(details)} align="center">
          <FileUpload.HiddenInput />
          <FileUpload.Trigger asChild>
            <Box w="100%" display="flex" justifyContent="center">
              <Button>Load Image</Button>
            </Box>
          </FileUpload.Trigger>
        </FileUpload.Root>
      </VStack>

      <VStack>
        <Heading as="h3" size="md">
          Sheet Side
        </Heading>
        <RadioGroup.Root value={sheetSide} onValueChange={(details) => setSheetSide(details.value)}>
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
            plotTime={1}
            stones={[
              {
                color: "green",
                position_history: [
                  [sheetCoordinatesData[0], sheetCoordinatesData[1]],
                  [sheetCoordinatesData[0], sheetCoordinatesData[1]],
                ],
                time_history: [0, 100],
              },
            ]}
            sheetPlotYExtent={sheetSide === "away" ? [-1, 65] : [-65, 1]}
          />
        </VStack>
      </VStack>
    </HStack>
  );
};

export default TestCalibration;
