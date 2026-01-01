import {Tabs, HStack, Separator, Spacer } from "@chakra-ui/react"

import CameraSetup from "../CameraSetup/CameraSetup";
import SingleImageDetect from "../SingleImageDetect/SingleImageDetect";

const TopLevel = () => {
  return (
        <HStack alignItems="start" spacing="10px" width="100%">
          <Tabs.Root defaultValue="calibration" width="100%">
              <Tabs.List>
                <Tabs.Trigger value="single-image-detect">Single Image Detect</Tabs.Trigger>
                <Tabs.Trigger value="camera_setup">Camera Setup</Tabs.Trigger>
              </Tabs.List>
              <Tabs.Content value="single-image-detect">
                <SingleImageDetect/>
              </Tabs.Content>
              <Tabs.Content value="camera_setup">
                <CameraSetup/>
              </Tabs.Content>
          </Tabs.Root>
          <Spacer />
          <Separator orientation="vertical" height="100%"/>
        </HStack>
  );

};

export default TopLevel;