import React, { useState } from "react";

import {VStack, Heading } from "@chakra-ui/react"

import FetchDropdown from '../FetchDropdown/FetchDropdown';


const Settings = ({cameraId, setCameraId}) => {

  return (
    <div>
        <VStack>
            <Heading>Settings</Heading>
            <FetchDropdown api_url="/api/camera_ids" 
                           jsonToList={(json) => json}
                           itemToKey={(id) => id}
                           itemToString={(id) => id}
                           label="Camera Calibration"
                           placeholder="Select Camera Id"
                           value={cameraId}
                           setValue={setCameraId}/>
        </VStack>
    </div>
  );
};

export default Settings;