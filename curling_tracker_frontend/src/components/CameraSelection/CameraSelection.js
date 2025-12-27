import React, { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

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

  const fetchCameraSetup = async (setupId) => {
    const params = new URLSearchParams({ setup_id: setupId});
    const response = await fetch('/api/camera_setup?' + params, {
                                  method: 'GET',
                                  headers: {
                                    'Content-Type': 'application/json',
                                  },
                                });
    if (!response.ok) {
        throw new Error('Network response was not ok');
    }

    return response.json();
  }

const CameraSelection = () => {
  const [selectedSetupId, setSelectedSetupId] = useState("");

  const [editing, setEditing] = useState("none");

  const [setupName, setSetupName] = useState('');
  const [cameras, setCameras] = useState([]);
  const [selectedCameraIndex, setSelectedCameraIndex] = useState(-1);
  const [image, setImage] = useState(null);
  const [cornerSelected, setCornerSelected] = useState(null);

  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: createSetup,
    onSuccess: (data) => {
      setSelectedSetupId(data.setup_id);
      queryClient.invalidateQueries({ queryKey: ['/api/camera_setup_headers'] });
    },
  });

  const { data, error, isLoading } = useQuery({
                              queryKey: ['/api/camera_setup', selectedSetupId],
                              queryFn: () => fetchCameraSetup(selectedSetupId),
                              initialData: null,
                              enabled: selectedSetupId !== "",
                              timeToStale: Infinity,                            
                            });

  const resetToServerData = () => {
    if (data) {
      setSetupName(data.setup_name);
      setCameras(data.cameras || []);
      setSelectedCameraIndex(-1);
      setImage(null);
    } else {
      setSetupName('');
      setCameras([]);
      setSelectedCameraIndex(-1);
      setImage(null);
    }
  }

  useEffect(() => {
    resetToServerData();
  }, [data]);

  const addNewCamera = () => {
    const newCamera = {
      camera_name: `Camera ${cameras.length + 1}`,
      corner1: [0,0],
      corner2: [0,0],
    };
    setCameras([...cameras, newCamera]);
  };

  const onFinishEditing = () => {
    if (editing === "new") {
      mutation.mutate({setup_name: setupName, cameras: cameras});
    } else if (editing === "existing") {
      mutation.mutate({setup_id: selectedSetupId, setup_name: setupName, cameras: cameras});
    }
    setEditing("none");
  }

  const onDiscardEditing = () => {
    resetToServerData();
    setEditing("none");
  }

  const onNewCameraSetup = () => {
    setEditing("new");
    setSetupName('');
    setCameras([]);
    setSelectedCameraIndex(-1);
    setImage(null);
  }

  const onImageClick = (x,y) => {
    if (selectedCameraIndex === -1 || cornerSelected === null) {
      return;
    }
    const updatedCameras = [...cameras];
    updatedCameras[selectedCameraIndex][cornerSelected] = [Math.trunc(x), Math.trunc(y)];
    setCameras(updatedCameras);
  };

  return (
    <HStack alignItems="start" spacing="20px">
      <VStack alignItems="start" spacing="10px" marginRight="20px">
        <Button onClick={onNewCameraSetup}
                display={editing === "none" ? "flex" : "none"}>New Camera Setup</Button>
        <HStack display={editing === "none" ? "flex" : "none"}>
          <FetchDropdown api_url="/api/camera_setup_headers" 
                         placeholder="Select Camera Setup"
                         jsonToList={(json) => json}
                         itemToKey={(item) => item.setup_id}
                         itemToString={(item) => item.setup_name}
                         value={selectedSetupId}
                         setValue={setSelectedSetupId}/>

          <Button onClick={() => setEditing("existing")} disabled={selectedSetupId === ""}>Edit</Button>
        </HStack>

        <Field.Root required display={editing !== "none" ? "flex" : "none"}>
          <Field.Label>
            Name <Field.RequiredIndicator />
          </Field.Label>
          <Input placeholder="Enter Camera Setup Name" value={setupName} onChange={(e) => setSetupName(e.target.value)} />
        </Field.Root>

        <HStack display={editing !== "none" ? "flex" : "none"}>
          <Button onClick={onFinishEditing}>Finish</Button>
          <Button onClick={onDiscardEditing}>Discard</Button>
        </HStack>
      </VStack>

      <VStack alignItems="start" spacing="10px">
        {selectedCameraIndex !== -1 && (
          <VStack display={selectedCameraIndex !== -1 ? "flex" : "none"}>
            <Field.Root required orientation="horizontal" disabled={editing === "none"}>
              <Field.Label>Name</Field.Label>
              <Input value={cameras[selectedCameraIndex].camera_name} onChange={(e) => {
                    const updatedCameras = [...cameras];
                    updatedCameras[selectedCameraIndex].camera_name = e.target.value;
                    setCameras(updatedCameras);
                  }}/>            
            </Field.Root>

            <Field.Root required orientation="horizontal" disabled={editing === "none"}>
              <Field.Label>Corner 1</Field.Label>
              <Input value={cameras[selectedCameraIndex].corner1} onChange={(e) => {
                    const updatedCameras = [...cameras];
                    const [xStr, yStr] = e.target.value.split(',').map(s => s.trim());
                    updatedCameras[selectedCameraIndex].corner1 = [parseFloat(Math.trunc(xStr)), parseFloat(Math.trunc(yStr))];
                    setCameras(updatedCameras);
                  }}
                  onFocus={() => setCornerSelected("corner1")} />            
            </Field.Root>

            <Field.Root required orientation="horizontal" disabled={editing === "none"}>
              <Field.Label>Corner 2</Field.Label>
              <Input value={cameras[selectedCameraIndex].corner2} onChange={(e) => {
                    const updatedCameras = [...cameras];
                    const [xStr, yStr] = e.target.value.split(',').map(s => s.trim());
                    updatedCameras[selectedCameraIndex].corner2 = [parseFloat(Math.trunc(xStr)), parseFloat(Math.trunc(yStr))];
                    setCameras(updatedCameras);
                  }} 
                  onFocus={() => setCornerSelected("corner2")}/>            
            </Field.Root>
          </VStack>
        )}

        <Text>Cameras</Text>
        {cameras.map((camera, index) => (
          <Button key={index} width="200px" justifyContent="flex-start" 
                  onClick={() => setSelectedCameraIndex(index)} variant={selectedCameraIndex === index ? "solid" : "outline"}>
            {camera.camera_name}
          </Button>
        ))}
        
        <Button onClick={addNewCamera}
                display={editing !== "none" ? "flex" : "none"}>Add Camera</Button>
      </VStack>

      <Box display={editing !== "none" ? "grid" : "none"}
          position="relative">
        {selectedCameraIndex !== -1 && (<Box
            position="absolute"
            left={Math.min(cameras[selectedCameraIndex].corner1[0], cameras[selectedCameraIndex].corner2[0]) + "px"}
            top={Math.min(cameras[selectedCameraIndex].corner1[1], cameras[selectedCameraIndex].corner2[1]) + "px"}
            width={Math.abs(cameras[selectedCameraIndex].corner2[0] - cameras[selectedCameraIndex].corner1[0]) + "px"}
            height={Math.abs(cameras[selectedCameraIndex].corner2[1] - cameras[selectedCameraIndex].corner1[1]) + "px"}
            bg="black"
            opacity="0.5"
            pointerEvents="none"
          />)}
        <ImageViewer position="absolute" file={image} onFileChange={(details) => setImage(details.acceptedFiles[0])}
                      onImageClick={onImageClick}>
          
        </ImageViewer>
      </Box>
    </HStack>
  );
};

export default CameraSelection;