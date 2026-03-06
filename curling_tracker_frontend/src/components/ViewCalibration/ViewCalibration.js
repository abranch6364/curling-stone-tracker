import { useState, useEffect, useRef } from "react";
import { useQueryClient, useQuery } from "@tanstack/react-query";
import { Button, HStack, VStack, Text, Heading } from "@chakra-ui/react";

import MatrixDisplay from "../MatrixDisplay/MatrixDisplay";
import FetchDropdown from "../FetchDropdown/FetchDropdown";

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

const ViewCalibration = ({ selectedSetupId, setSelectedSetupId }) => {
  const [selectedCameraIndex, setSelectedCameraIndex] = useState(-1);

  const inputRefs = useRef({});
  const queryClient = useQueryClient();

  //////////////////
  //Helper Functions
  //////////////////
  const isCameraSelected = () => {
    return selectedCameraIndex !== -1;
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

  ///////////
  //Callbacks
  ///////////
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
        <Heading as="h2" size="lg">
          Calibration Data
        </Heading>

        <Heading as="h3" size="md">
          Camera Matrix
        </Heading>
        {isCameraSelected() && data.cameras[selectedCameraIndex].camera_matrix && (
          <MatrixDisplay matrix={data.cameras[selectedCameraIndex].camera_matrix}></MatrixDisplay>
        )}

        <Heading as="h3" size="md">
          Rotation Vectors
        </Heading>
        {isCameraSelected() && data.cameras[selectedCameraIndex].rotation_vectors && (
          <MatrixDisplay matrix={data.cameras[selectedCameraIndex].rotation_vectors}></MatrixDisplay>
        )}

        <Heading as="h3" size="md">
          Translation Vectors
        </Heading>
        {isCameraSelected() && data.cameras[selectedCameraIndex].translation_vectors && (
          <MatrixDisplay matrix={data.cameras[selectedCameraIndex].translation_vectors}></MatrixDisplay>
        )}

        <Heading as="h3" size="md">
          Distortion Coefficients
        </Heading>
        {isCameraSelected() && data.cameras[selectedCameraIndex].distortion_coefficients && (
          <MatrixDisplay matrix={data.cameras[selectedCameraIndex].distortion_coefficients}></MatrixDisplay>
        )}
      </VStack>
    </HStack>
  );
};

export default ViewCalibration;
