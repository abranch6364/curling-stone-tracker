import React, { useState } from "react";

import { useQuery } from '@tanstack/react-query';
import Settings from '../Settings/Settings';
import Calibration from '../Calibration/Calibration';
import {Tabs, HStack, Text, Separator, Spacer } from "@chakra-ui/react"
import SingleImageDetect from "../SingleImageDetect/SingleImageDetect";

const TopLevel = () => {
  const [settingsCameraId, setSettingsCameraId] = useState("");

  const fetchCameraCalibration = async () => {
    const params = new URLSearchParams({ camera_id: settingsCameraId});
    console.log("fetchCameraCalibration: ", settingsCameraId);
    const response = await fetch('/api/camera_calibration?' + params, {
                                  method: 'GET',
                                  headers: {
                                    'Content-Type': 'application/json',
                                  },
                                });
    if (!response.ok) {
        throw new Error('Network response was not ok');
    }

    return response.json();
  }

  const { data, error, isLoading } = useQuery({
                              queryKey: ['/api/camera_calibration', settingsCameraId],
                              queryFn: () => fetchCameraCalibration(),
                              initialData: null,
                              enabled: settingsCameraId !== "",
                            });

  return (
        <HStack alignItems="start" spacing="10px" width="100%">
          <Tabs.Root defaultValue="calibration" width="100%">
              <Tabs.List>
                <Tabs.Trigger value="calibration">Calibration</Tabs.Trigger>
                <Tabs.Trigger value="single-image-detect">Single Image Detect</Tabs.Trigger>
              </Tabs.List>
              <Tabs.Content value="calibration">
                <Calibration cameraCalibration={data}
                             setCameraId={setSettingsCameraId}/>
              </Tabs.Content>
              <Tabs.Content value="single-image-detect">
                <SingleImageDetect cameraCalibration={data} />
              </Tabs.Content>
          </Tabs.Root>
          <Spacer />
          <Separator orientation="vertical" height="100%"/>
          <Settings marginLeft="auto"
                    cameraId={settingsCameraId} 
                    setCameraId={setSettingsCameraId}/>
        </HStack>
  );

};

export default TopLevel;