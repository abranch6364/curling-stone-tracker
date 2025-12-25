import React, { useState, useEffect, useRef } from "react";

import { Button, Input, HStack, VStack, Text, Heading } from "@chakra-ui/react"

import ImageViewer from "../ImageViewer/ImageViewer";
import CurlingSheetPlot from "../CurlingSheetPlot/CurlingSheetPlot";
import { useQueryClient, useQuery } from '@tanstack/react-query';


const SingleImageDetect = ({cameraCalibration}) => {
  const [file, setFile] = useState(null);

  const queryClient = useQueryClient();

  const fetchDetections = async () => {
    const formData = new FormData();
    formData.append('file', file); 
    formData.append('camera_id', cameraCalibration.camera_id);

    const response = await fetch('/api/detect_stones', {
                                  method: 'POST',
                                  body: formData,
                                });
    if (!response.ok) {
        throw new Error('Network response was not ok');
    }

    return response.json();
  }

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

    const a = document.createElement('a');
    const blob = new Blob([textContent], { type: 'text/plain' });
    a.href = URL.createObjectURL(blob);
    a.download = 'chess_on_ice_positions.txt';
    a.click();
  };

  const { data, error, isLoading } = useQuery({
                              queryKey: ['/api/single_image_detect'],
                              queryFn: () => fetchDetections(),
                              initialData: null,
                              enabled: file !== null,
                            });

  return (
    <HStack>
      <ImageViewer file={file} onFileChange={(details) => setFile(details.acceptedFiles[0])} />
      <VStack>
        <CurlingSheetPlot stones={data ? data["stones"] : []} />
        <HStack>
          <Button onClick={() => queryClient.invalidateQueries(['/api/single_image_detect'])}>Detect Rocks</Button>
          <Button onClick={() => outputChessOnIceStonePositions(data ? data["stones"] : [])}>Output Chess On Ice Positions</Button>
        </HStack>
      </VStack>
    </HStack>
  );
};

export default SingleImageDetect;