import { useState } from "react";
import { useQueryClient, useQuery } from "@tanstack/react-query";
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

        <Field.Root orientation="horizontal">
          <Field.Label>Youtube Link</Field.Label>
          <Input value={videoLink} onChange={(e) => setVideoLink(e.target.value)} />
        </Field.Root>

        <Field.Root orientation="horizontal">
          <Field.Label>Start Time</Field.Label>
          <TimeInput onChangeTotalSeconds={setStartTime} />
        </Field.Root>

        <Field.Root orientation="horizontal">
          <Field.Label>Duration</Field.Label>
          <TimeInput onChangeTotalSeconds={setDuration} />
        </Field.Root>

        <Button onClick={() => queryClient.invalidateQueries(["/api/request_video_tracking"])}>
          Request Video Analysis
        </Button>
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
