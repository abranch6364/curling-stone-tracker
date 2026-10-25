import { useQuery } from "@tanstack/react-query";
import { Tabs, HStack, Separator, Spacer, Spinner, Text } from "@chakra-ui/react";

import CameraSetup from "../CameraSetup/CameraSetup";
import VideoDetect from "../VideoDetect/VideoDetect";
import TrackVideos from "../TrackVideos/TrackVideos";
import Draws from "../Draws/Draws";

import { fetchJson } from "../../utility/TrackingRunHelper";

const TopLevel = () => {
  // A read only server only serves the tracked draws, so only the Draws tab is shown
  const { data: config, error } = useQuery({
    queryKey: ["config"],
    queryFn: () => fetchJson("/api/config"),
    staleTime: Infinity,
  });

  if (error) {
    return <Text color="fg.error">Failed to reach the server: {error.message}</Text>;
  }
  if (!config) {
    return <Spinner />;
  }

  if (config.read_only) {
    return (
      <Tabs.Root defaultValue="draws" width="100%">
        <Tabs.List>
          <Tabs.Trigger value="draws">Draws</Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="draws">
          <Draws />
        </Tabs.Content>
      </Tabs.Root>
    );
  }

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
