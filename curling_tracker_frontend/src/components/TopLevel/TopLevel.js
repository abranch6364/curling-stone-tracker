import { Tabs, HStack, Separator, Spacer } from "@chakra-ui/react";

import CameraSetup from "../CameraSetup/CameraSetup";
import VideoDetect from "../VideoDetect/VideoDetect";
import TrackVideos from "../TrackVideos/TrackVideos";
import Draws from "../Draws/Draws";

const TopLevel = () => {
  return (
    <HStack alignItems="start" spacing="10px" width="100%">
      <Tabs.Root defaultValue="calibration" width="100%">
        <Tabs.List>
          <Tabs.Trigger value="video-detect">Video Detect</Tabs.Trigger>
          <Tabs.Trigger value="track-videos">Track Videos</Tabs.Trigger>
          <Tabs.Trigger value="draws">Draws</Tabs.Trigger>
          <Tabs.Trigger value="camera_setup">Camera Setup</Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="video-detect">
          <VideoDetect />
        </Tabs.Content>
        <Tabs.Content value="track-videos">
          <TrackVideos />
        </Tabs.Content>
        <Tabs.Content value="draws">
          <Draws />
        </Tabs.Content>
        <Tabs.Content value="camera_setup">
          <CameraSetup />
        </Tabs.Content>
      </Tabs.Root>
      <Spacer />
      <Separator orientation="vertical" height="100%" />
    </HStack>
  );
};

export default TopLevel;
