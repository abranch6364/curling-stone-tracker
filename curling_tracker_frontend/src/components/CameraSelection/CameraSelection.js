import React, { useState } from "react";
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { HStack, VStack, Button, Field, Input, Box, Text } from "@chakra-ui/react"
import FetchDropdown from "../FetchDropdown/FetchDropdown";
import ImageViewer from "../ImageViewer/ImageViewer";

const createSetup = async (newSetup) => {
  const response = await fetch('/api/camera_setup', {
                                method: 'POST',
                                headers: {
                                  'Content-Type': 'application/json',
                                },

                                body: JSON.stringify(newSetup),
                              });
  return response.json();
}

const CameraSelection = () => {
  const [editing, setEditing] = useState(false);
  const [setupName, setSetupName] = useState('');
  const [image, setImage] = useState(null);
  const [cameras, setCameras] = useState([]);
  const [selectedCameraIndex, setSelectedCameraIndex] = useState(-1);

  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: createSetup,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/camera_setup_headers'] });
    },
  });

  const addNewCamera = () => {
    const newCamera = {
      name: `Camera ${cameras.length + 1}`,
    };
    setCameras([...cameras, newCamera]);
  };

  const onFinishEditing = () => {
    setEditing(false);
    mutation.mutate({name: setupName, cameras: cameras});
  }

  const onDiscardEditing = () => {
    setEditing(false);
    setSetupName('');
    setImage(null);
    setCameras([]);
    setSelectedCameraIndex(-1);
  }

  return (
    <HStack alignItems="start" spacing="20px">
      <VStack alignItems="start" spacing="10px" marginRight="20px">
        <Button onClick={() => setEditing(true)}
                display={!editing ? "flex" : "none"}>New Camera Setup</Button>
        <HStack display={!editing ? "flex" : "none"}>
          <FetchDropdown api_url="/api/camera_setup_headers" 
                         placeholder="Select Camera Setup"
                         jsonToList={(json) => json}
                         itemToKey={(item) => item.setup_id}
                         itemToString={(item) => item.setup_name}></FetchDropdown>
          <Button onClick={() => setEditing(true)}>Edit</Button>
        </HStack>

        <Field.Root required display={editing ? "flex" : "none"}>
          <Field.Label>
            Name <Field.RequiredIndicator />
          </Field.Label>
          <Input placeholder="Enter Camera Setup Name" value={setupName} onChange={(e) => setSetupName(e.target.value)} />
        </Field.Root>
        <HStack display={editing ? "flex" : "none"}>
          <Button onClick={onFinishEditing}>Finish</Button>
          <Button onClick={onDiscardEditing}>Discard</Button>
        </HStack>
      </VStack>
      <VStack alignItems="start" spacing="10px" display={editing ? "flex" : "none"}>
        {selectedCameraIndex !== -1 && (
          <Box display={selectedCameraIndex !== -1 ? "flex" : "none"}>
            <Field.Root required orientation="horizontal">
              <Field.Label>Name</Field.Label>
              <Input value={cameras[selectedCameraIndex].name} onChange={(e) => {
                    const updatedCameras = [...cameras];
                    updatedCameras[selectedCameraIndex].name = e.target.value;
                    setCameras(updatedCameras);
                  }} />            
            </Field.Root>
          </Box>
        )}

        <Text>Cameras</Text>
        {cameras.map((camera, index) => (
          <Button key={index} width="200px" justifyContent="flex-start" 
                  onClick={() => setSelectedCameraIndex(index)} variant={selectedCameraIndex === index ? "solid" : "outline"}>
            {camera.name}
          </Button>
        ))}
        
        <Button onClick={addNewCamera}>Add Camera</Button>
      </VStack>
      <Box display={editing ? "flex" : "none"}>
        <ImageViewer file={image} onFileChange={(details) => setImage(details.acceptedFiles[0])}></ImageViewer>
      </Box>
    </HStack>
  );
};

export default CameraSelection;