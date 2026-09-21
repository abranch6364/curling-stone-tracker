import { useState } from "react";
import { Tabs, VStack, HStack, FileUpload, Box, Button, Input, Field } from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";

import CameraSelection from "../CameraSelection/CameraSelection";
import CreateCalibration from "../CreateCalibration/CreateCalibration";
import ViewCalibration from "../ViewCalibration/ViewCalibration";
import TestCalibration from "../TestCalibration/TestCalibration";

const fetchVideoImage = async (video_url, timestamp) => {
  const params = new URLSearchParams({ video_url: video_url, timestamp: timestamp });
  const response = await fetch("/api/video_frame?" + params, {
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

const CameraSetup = () => {
  const [setupId, setSetupId] = useState("");
  const [videoUrl, setVideoUrl] = useState("");
  const [calibrationImage, setCalibrationImage] = useState(null);

  const onImageFileChange = (details) => {
    setCalibrationImage(details.acceptedFiles[0]);
  };

  const loadImageFromURL = async () => {
    const { data: downloadedData } = await refetch();
    if (downloadedData) {
      setCalibrationImage(downloadedData["frame"]);
    }
  };

  const { refetch, isFetching } = useQuery({
    queryKey: ["/api/video_frame", videoUrl],
    queryFn: () => fetchVideoImage(videoUrl, 60),
    initialData: null,
    enabled: false,
    timeToStale: Infinity,
  });

  return (
    <VStack>
      <HStack>
        <FileUpload.Root onFileChange={(details) => onImageFileChange(details)} align="center">
          <FileUpload.HiddenInput />
          <FileUpload.Trigger asChild>
            <Box w="100%" display="flex" justifyContent="center">
              <Button>Load Image</Button>
            </Box>
          </FileUpload.Trigger>
        </FileUpload.Root>

        <VStack>
          <Field.Root required display={"flex"}>
            <Field.Label>
              Video URL <Field.RequiredIndicator />
            </Field.Label>
            <Input placeholder="Enter Video URL" value={videoUrl} onChange={(e) => setVideoUrl(e.target.value)} />
          </Field.Root>

          <Button onClick={loadImageFromURL} disabled={isFetching}>
            {isFetching ? "Loading..." : "Load Image From Video"}
          </Button>
        </VStack>
      </HStack>

      <Tabs.Root defaultValue="camera_selection" width="100%">
        <Tabs.List>
          <Tabs.Trigger value="camera_selection">Camera Selection</Tabs.Trigger>
          <Tabs.Trigger value="create_calibration">Create Calibration</Tabs.Trigger>
          <Tabs.Trigger value="view_calibration">View Calibration</Tabs.Trigger>
          <Tabs.Trigger value="test_calibration">Test Calibration</Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="camera_selection">
          <CameraSelection
            selectedSetupId={setupId}
            setSelectedSetupId={setSetupId}
            calibrationImage={calibrationImage}
          ></CameraSelection>
        </Tabs.Content>
        <Tabs.Content value="create_calibration">
          <CreateCalibration
            selectedSetupId={setupId}
            setSelectedSetupId={setSetupId}
            calibrationImage={calibrationImage}
          ></CreateCalibration>
        </Tabs.Content>
        <Tabs.Content value="view_calibration">
          <ViewCalibration selectedSetupId={setupId} setSelectedSetupId={setSetupId}></ViewCalibration>
        </Tabs.Content>

        <Tabs.Content value="test_calibration">
          <TestCalibration
            selectedSetupId={setupId}
            setSelectedSetupId={setSetupId}
            calibrationImage={calibrationImage}
          ></TestCalibration>
        </Tabs.Content>
      </Tabs.Root>
    </VStack>
  );
};

export default CameraSetup;
