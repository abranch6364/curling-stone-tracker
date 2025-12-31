import React, { useState, useEffect, useRef } from "react";
import "./Calibration.css";

import { Button, Input, HStack, VStack, Text, Heading, FileUpload, Box, RadioGroup } from "@chakra-ui/react"

import ImageViewer from "../ImageViewer/ImageViewer";
import MatrixDisplay from '../MatrixDisplay/MatrixDisplay';
import FetchDropdown from '../FetchDropdown/FetchDropdown';

import { useQueryClient, useQuery } from '@tanstack/react-query';

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

const Calibration = ({selectedSetupId, setSelectedSetupId}) => {
    const [fullImage, setFullImage] = useState(null);
    const [splitImages, setSplitImages] = useState(null);
    const [pointFilter, setPointFilter] = useState('home')
    const [selectedCameraIndex, setSelectedCameraIndex] = useState(-1);

    const [sheetCoords, setSheetCoords] = useState({});
    const [imageCoords, setImageCoords] = useState({});
    const [selectedKey, setSelectedKey] = useState('');
    const inputRefs = useRef({})
    const [imageDimensions, setImageDimensions] = useState({ height: 0, width: 0 });

    const queryClient = useQueryClient();

    const { data, error, isLoading } = useQuery({
                                queryKey: ['/api/camera_setup', selectedSetupId],
                                queryFn: () => fetchCameraSetup(selectedSetupId),
                                initialData: null,
                                enabled: selectedSetupId !== "",
                                timeToStale: Infinity,                            
                              });

    const setImageCoordsKey = (key, value) => {
      const nextImageCoords = Object.entries(imageCoords).map(([k, v]) => {
        if (k === key) {
          return [k, value];
        } else {
          return [k, v];
        }
      });
      setImageCoords(Object.fromEntries(nextImageCoords));
    }
  
    const inputHandleChange = (event, key) => {
      setImageCoordsKey(key, event.target.value);
    };

    useEffect(() => {
      fetch('/api/sheet_coordinates')
        .then(response => response.json())
        .then(json => {setSheetCoords(json);
                       setImageCoords(Object.fromEntries(Object.keys(json).map(key => [key, ''])));
                      })
        .catch(error => console.error(error));
    }, []);


    const splitImageByCamera = (image) => {

      var imageElement = new Image();
      imageElement.onload = splitImage;
      imageElement.src = URL.createObjectURL(image);
      
      function splitImage() {
        var newSplitImages = {}
        for(const c of data.cameras) {
          var canvas = document.createElement('canvas');
          var xOrigin = Math.min(c.corner1[0], c.corner2[0]);
          var yOrigin = Math.min(c.corner1[1], c.corner2[1]);
          canvas.width = Math.abs(c.corner1[0] - c.corner2[0]);
          canvas.height = Math.abs(c.corner1[1] - c.corner2[1]);

          var context = canvas.getContext('2d');
          context.drawImage(imageElement, xOrigin, yOrigin, canvas.width, canvas.height, 0, 0, canvas.width, canvas.height);
          newSplitImages[c.camera_id] = canvas.toDataURL();
        }
        setSplitImages(newSplitImages);
      }

    }

    useEffect(() => {
      if(fullImage !== null && data !== null) {
        splitImageByCamera(fullImage);
      }
    }, [data]);

  
    const calibrateCamera = () => {
      if(!data || selectedCameraIndex === -1) {
        return;
      }

      console.log('Calibrating Camera');
      let remappedImageCoords = Object.fromEntries(Object.entries(imageCoords).filter(([key, coordStr]) => coordStr !== '')
              .map(([key, coordStr]) => {
                const [xStr, yStr] = coordStr.split(',').map(s => s.trim());
                return [key, [parseFloat(xStr), parseFloat(yStr)]];
              }));
      fetch('/api/camera_calibration', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
  
          body: JSON.stringify({
            camera_id: data.cameras[selectedCameraIndex].camera_id,
            image_points: remappedImageCoords,
            world_points: sheetCoords,
            image_shape: [imageDimensions.width, imageDimensions.height]
          }),
        })
        .then(response => response.json())
        .then(() => {queryClient.invalidateQueries({ queryKey: ['/api/camera_setup'] })})
        .catch(error => console.error(error));
    };

    const imageViewerClick = (x,y) => {
      if (!(selectedKey in sheetCoords)) {
        return;
      }
      setImageCoordsKey(selectedKey, `${Math.trunc(x)}, ${Math.trunc(y)}`);
      inputRefs.current[selectedKey].focus();
    }

    const onImageFileChange = (details) => {
      setFullImage(details.acceptedFiles[0]);
      if(details.acceptedFiles[0] !== null && data !== null) {
        splitImageByCamera(details.acceptedFiles[0]);
      }
    }

    const onCameraButtonClick = (index) => {
      console.log("ON CAMERA CLICK");
      setSelectedCameraIndex(index);
      
      const nextImageCoords = Object.entries(imageCoords).map(([k, v]) => {
          return [k, ""];
      });
      setImageCoords(Object.fromEntries(nextImageCoords));
    }

    const onDropdownChange = (value) => {
      setSelectedCameraIndex(-1);
      setSelectedSetupId(value);
    }
  
  return (
    <HStack alignItems="start">
        <VStack alignItems="start" spacing="10px" marginRight="20px">
          <Heading size="md">Selected Camera Setup</Heading>
          <FetchDropdown api_url="/api/camera_setup_headers" 
                placeholder="Select Camera Setup"
                jsonToList={(json) => json}
                itemToKey={(item) => item.setup_id}
                itemToString={(item) => item.setup_name}
                value={selectedSetupId}
                setValue={onDropdownChange}/>

        <Text>Cameras</Text>
        {data && data.cameras.map((camera, index) => (
          <Button key={index} width="200px" justifyContent="flex-start" 
                  onClick={() => onCameraButtonClick(index)} variant={selectedCameraIndex === index ? "solid" : "outline"}>
            {camera.camera_name}
          </Button>
        ))}

        </VStack>
        <VStack>
          <ImageViewer onImageClick={imageViewerClick} 
                      setImageDimensions={setImageDimensions}
                      file={(selectedCameraIndex !== -1 && splitImages !== null && data) ? splitImages[data.cameras[selectedCameraIndex].camera_id] : null}
          />
          <FileUpload.Root onFileChange={(details) => onImageFileChange(details)} align="center">
            <FileUpload.HiddenInput />
            <FileUpload.Trigger asChild>
              <Box w="100%" display="flex" justifyContent="center">
                <Button>
                  Load Image
                </Button>
              </Box>
            </FileUpload.Trigger>
          </FileUpload.Root>
        </VStack>

        
        <VStack align="start">
          <Heading as="h3" size="md">Filter Points By Side</Heading>
          <RadioGroup.Root defaultValue="home" value={pointFilter} onValueChange={(details) => setPointFilter(details.value)}>
              <VStack gap="6">
                {["home", "away"].map((item) => (
                  <RadioGroup.Item key={item} value={item}>
                    <RadioGroup.ItemHiddenInput />
                    <RadioGroup.ItemIndicator />
                    <RadioGroup.ItemText>{item}</RadioGroup.ItemText>
                  </RadioGroup.Item>
                ))}
              </VStack>
            </RadioGroup.Root>
            {Object.keys(sheetCoords).map((key) => (
              key.includes(pointFilter) && <div key={key}>
                  <HStack>
                      <Text fontWeight="bold">{key}:</Text>
                      <Input
                          size="xs"
                          type="text"
                          ref={el => inputRefs.current[key] = el}
                          value={imageCoords[key]}
                          onChange={(e) => inputHandleChange(e, key)}
                          onFocus={() => setSelectedKey(key)}
                      />
                  </HStack>
              </div>
            ))}
        </VStack>
        <VStack>
            <Heading as="h2" size="lg">Calibration Data</Heading>

            <Heading as="h3" size="md">Camera Matrix</Heading>
            {selectedCameraIndex !== -1 && data.cameras[selectedCameraIndex].camera_matrix && <MatrixDisplay matrix={data.cameras[selectedCameraIndex].camera_matrix}></MatrixDisplay>}

            <Heading as="h3" size="md">Rotation Vectors</Heading>
            {selectedCameraIndex !== -1 && data.cameras[selectedCameraIndex].rotation_vectors && <MatrixDisplay matrix={data.cameras[selectedCameraIndex].rotation_vectors}></MatrixDisplay>}

            <Heading as="h3" size="md">Translation Vectors</Heading>
            {selectedCameraIndex !== -1 && data.cameras[selectedCameraIndex].translation_vectors && <MatrixDisplay matrix={data.cameras[selectedCameraIndex].translation_vectors}></MatrixDisplay>}

            <Heading as="h3" size="md">Distortion Coefficients</Heading>
            {selectedCameraIndex !== -1 && data.cameras[selectedCameraIndex].distortion_coefficients && <MatrixDisplay matrix={data.cameras[selectedCameraIndex].distortion_coefficients}></MatrixDisplay>}

            <Button onClick={calibrateCamera}>
            Compute Camera Calibration
            </Button>
        </VStack>
    </HStack>
  );
};

export default Calibration;