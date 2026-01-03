import { useState } from "react";
import { useQueryClient, useMutation } from "@tanstack/react-query";
import { Button, HStack, VStack, Heading, RadioGroup, Field, Input } from "@chakra-ui/react";

import CurlingSheetPlot from "../CurlingSheetPlot/CurlingSheetPlot";
import FetchDropdown from "../FetchDropdown/FetchDropdown";
import TimeInput from "../TimeInput/TimeInput";

const VideoDetect = () => {
  const [setupId, setSetupId] = useState("");
  const [sheetSide, setSheetSide] = useState("away");

  const [videoLink, setVideoLink] = useState("");
  const [startTime, setStartTime] = useState(0);
  const [duration, setDuration] = useState(0);

  const queryClient = useQueryClient();

  //////////////////
  //Helper Functions
  //////////////////
  const requestVideoTracking = async (video_tracking_request) => {
    const response = await fetch("/api/request_video_tracking", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify(video_tracking_request),
    });
    return response.json();
  };

  ///////////////
  //Use Functions
  ///////////////

  const mutation = useMutation({
    mutationFn: requestVideoTracking,
    onSuccess: (data) => {
      queryClient.invalidateQueries({
        queryKey: ["/api/video_tracking_headers"],
      });
    },
  });

  ///////////
  //Callbacks
  ///////////
  const onTrackingRequestClick = () => {
    mutation.mutate({ url: videoLink, start_seconds: startTime, duration: duration, setup_id: setupId });
  };

  return (
    <HStack align="start">
      <VStack alignItems="start">
        <Heading as="h3" size="md">
          Select Camera Setup
        </Heading>
        <FetchDropdown
          api_url="/api/camera_setup_headers"
          placeholder="Select Camera Setup"
          jsonToList={(json) => json}
          itemToKey={(item) => item.setup_id}
          itemToString={(item) => item.setup_name}
          value={setupId}
          setValue={setSetupId}
        />

        <HStack>
          <Heading as="h3" size="md">
            Video URL
          </Heading>
          <Input value={videoLink} onChange={(e) => setVideoLink(e.target.value)} />
        </HStack>

        <HStack>
          <Heading as="h3" size="md">
            Start Time
          </Heading>
          <TimeInput onChangeTotalSeconds={setStartTime} />
        </HStack>

        <HStack>
          <Heading as="h3" size="md">
            Duration
          </Heading>
          <TimeInput onChangeTotalSeconds={setDuration} />
        </HStack>

        <Button onClick={onTrackingRequestClick}>Request Video Tracking</Button>
      </VStack>
      <VStack>
        <Heading as="h3" size="md">
          Sheet Side
        </Heading>
        <RadioGroup.Root defaultValue="away" value={sheetSide} onValueChange={(details) => setSheetSide(details.value)}>
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

        <CurlingSheetPlot
          //  stones={data ? data["stones"] : []}
          sheetPlotYExtent={sheetSide === "away" ? [35, 65] : [-65, -35]}
        />
      </VStack>
    </HStack>
  );
};

export default VideoDetect;
