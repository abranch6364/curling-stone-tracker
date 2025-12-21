import React, { useState, useEffect, useRef } from "react";

import { Button, Input, HStack, VStack, Text, Heading } from "@chakra-ui/react"

import ImageViewer from "../ImageViewer/ImageViewer";
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
        {data && <Text>{JSON.stringify(data)}</Text>}
        <Button onClick={() => queryClient.invalidateQueries(['/api/single_image_detect'])}>Detect Rocks</Button>
      </VStack>
    </HStack>
  );
};

export default SingleImageDetect;