import { useState } from "react";
import { useQueryClient, useQuery } from "@tanstack/react-query";
import { Button, HStack, VStack, Heading, RadioGroup } from "@chakra-ui/react";

import ImageViewer from "../ImageViewer/ImageViewer";
import CurlingSheetPlot from "../CurlingSheetPlot/CurlingSheetPlot";
import FetchDropdown from "../FetchDropdown/FetchDropdown";

const outputChessOnIceStonePositions = (stones) => {
  let textContent = "Positions";
  let greenStones = "A";
  let yellowStones = "B";
  const numberOfGreenStones = stones.filter((stone) => stone["color"] === "green").length;
  const numberOfYellowStones = stones.filter((stone) => stone["color"] === "yellow").length;

  for (const stone of stones) {
    let coords = null;
    if (stone.sheet_coordinates[1] > 0) {
      coords = `(${stone.sheet_coordinates[0].toFixed(2)},${(-(stone.sheet_coordinates[1] - 57.0)).toFixed(2)})`;
    } else {
      coords = `(${stone.sheet_coordinates[0].toFixed(2)},${(stone.sheet_coordinates[1] + 57.0).toFixed(2)})`;
    }

    if (stone["color"] === "green") {
      greenStones += `${coords}`;
    } else if (stone["color"] === "yellow") {
      yellowStones += `${coords}`;
    }
  }

  if (numberOfGreenStones > numberOfYellowStones) {
    yellowStones += "(!)".repeat(numberOfGreenStones - numberOfYellowStones);
  } else if (numberOfYellowStones > numberOfGreenStones) {
    greenStones += "(!)".repeat(numberOfYellowStones - numberOfGreenStones);
  }

  textContent += `\n${greenStones}\n${yellowStones}\n`;

  const a = document.createElement("a");
  const blob = new Blob([textContent], { type: "text/plain" });
  a.href = URL.createObjectURL(blob);
  a.download = "chess_on_ice_positions.txt";
  a.click();
};

const SingleImageDetect = () => {
  const [file, setFile] = useState(null);
  const [setupId, setSetupId] = useState("");
  const [sheetSide, setSheetSide] = useState("away");

  const queryClient = useQueryClient();

  //////////////////
  //Helper Functions
  //////////////////
  const fetchDetections = async () => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("setup_id", setupId);

    const response = await fetch("/api/detect_stones", {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      throw new Error("Network response was not ok");
    }

    return response.json();
  };

  ///////////////
  //Use Functions
  ///////////////
  const { data, error, isLoading } = useQuery({
    queryKey: ["/api/detect_stones"],
    queryFn: () => fetchDetections(),
    initialData: null,
    enabled: file !== null,
    timeToStale: Infinity,
  });

  return (
    <HStack align="start">
      <VStack>
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
      </VStack>
      <ImageViewer file={file} onFileChange={(details) => setFile(details.acceptedFiles[0])} includeLoadButton="true" />
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
          stones={data ? data["stones"] : []}
          sheetPlotYExtent={sheetSide === "away" ? [35, 65] : [-65, -35]}
        />
        <HStack>
          <Button onClick={() => queryClient.invalidateQueries(["/api/detect_stones"])}>Detect Rocks</Button>
          <Button onClick={() => outputChessOnIceStonePositions(data ? data["stones"] : [])}>
            Output Chess On Ice Positions
          </Button>
        </HStack>
      </VStack>
    </HStack>
  );
};

export default SingleImageDetect;
