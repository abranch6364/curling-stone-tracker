import React, { useState, useEffect, useRef } from "react";
import "./Calibration.css";

import { Button, Input, HStack, VStack, Text, Heading } from "@chakra-ui/react"

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
        .then(json => {setSheetCoords(json["side_a"]);
                       setImageCoords(Object.fromEntries(Object.keys(json["side_a"]).map(key => [key, ''])));
                      })
        .catch(error => console.error(error));
    }, []);
  
    const calibrateCamera = () => {
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
            image_points: remappedImageCoords,
            world_points: sheetCoords,
            image_shape: [imageDimensions.width, imageDimensions.height]
          }),
        })
        .then(response => response.json())
        .catch(error => console.error(error));
    };

    const imageViewerClick = (x,y) => {
      if (!(selectedKey in sheetCoords)) {
        return;
      }
      setImageCoordsKey(selectedKey, `${Math.trunc(x)}, ${Math.trunc(y)}`);
      inputRefs.current[selectedKey].focus();
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
                setValue={setSelectedSetupId}/>

        <Text>Cameras</Text>
        {data && data.cameras.map((camera, index) => (
          <Button key={index} width="200px" justifyContent="flex-start" 
                  onClick={() => setSelectedCameraIndex(index)} variant={selectedCameraIndex === index ? "solid" : "outline"}>
            {camera.camera_name}
          </Button>
        ))}

        </VStack>
        <ImageViewer onImageClick={imageViewerClick} 
                     setImageDimensions={setImageDimensions}
                     includeLoadButton="true"
        />

        <div className="PointList">
            {Object.keys(sheetCoords).map((key) => (
            <div key={key}>
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
        </div>
        <VStack>
            <Heading as="h2" size="lg">Calibration Data</Heading>

            <Heading as="h3" size="md">Camera Matrix</Heading>
            {null && <MatrixDisplay ></MatrixDisplay>}

            <Heading as="h3" size="md">Rotation Vectors</Heading>
            {null && <MatrixDisplay ></MatrixDisplay>}

            <Heading as="h3" size="md">Translation Vectors</Heading>
            {null && <MatrixDisplay ></MatrixDisplay>}

            <Heading as="h3" size="md">Distortion Coefficients</Heading>
            {null && <MatrixDisplay ></MatrixDisplay>}


            <Button onClick={calibrateCamera}>
            Compute Camera Calibration
            </Button>
        </VStack>
    </HStack>
  );
};

export default Calibration;