import React, { useState, useEffect, useRef } from "react";
import "./Calibration.css";

import { Button, Input, HStack, VStack, Text, Heading } from "@chakra-ui/react"

import ImageViewer from "../ImageViewer/ImageViewer";
import MatrixDisplay from '../MatrixDisplay/MatrixDisplay';
import FetchDropdown from '../FetchDropdown/FetchDropdown';
import { useQueryClient } from '@tanstack/react-query';


const Calibration = () => {
    const [sheetCoords, setSheetCoords] = useState({});
    const [imageCoords, setImageCoords] = useState({});
    const [selectedKey, setSelectedKey] = useState('');
    const [cameraCalibration, setCameraCalibration] = useState(null);
    const inputRefs = useRef({})
    const [imageDimensions, setImageDimensions] = useState({ height: 0, width: 0 });

    const queryClient = useQueryClient();

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
      let remappedImageCoords = Object.fromEntries(Object.entries(imageCoords).filter(([key, coordStr]) => coordStr !== '')
              .map(([key, coordStr]) => {
                const [xStr, yStr] = coordStr.split(',').map(s => s.trim());
                return [key, [parseFloat(yStr), parseFloat(xStr)]];
              }));
      fetch('/api/camera_calibration', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
  
          body: JSON.stringify({
            image_points: remappedImageCoords,
            world_points: sheetCoords,
            image_shape: [imageDimensions.height, imageDimensions.width]
          }),
        })
        .then(response => response.json())
        .then(json => {
          setCameraCalibration(json);
          queryClient.invalidateQueries({ queryKey: ['/api/camera_ids'] });
        })
        .catch(error => console.error(error));
    };
  
    const onDropdownChange = (event) => {
      const params = new URLSearchParams({ camera_id: event.target.value});
      fetch('/api/camera_calibration/?' + params, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        })
        .then(response => response.json())
        .then(json => setCameraCalibration(json));
    };

    const imageViewerClick = (x,y) => {
      if (!(selectedKey in sheetCoords)) {
        return;
      }
      setImageCoordsKey(selectedKey, `${Math.trunc(x)}, ${Math.trunc(y)}`);
      inputRefs.current[selectedKey].focus();
    }
  

  return (
    <div className="CalibrationContainer">
        <ImageViewer onImageClick={imageViewerClick} setDimensions={setImageDimensions}/>
        <div className="PointList">
            {Object.keys(sheetCoords).map((key) => (
            <div key={key}>
                <HStack>
                    <Text fontWeight="bold">{key}:</Text>
                    <Input
                        size="sm"
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
            <FetchDropdown api_url="/api/camera_ids" 
                           jsonToList={(json) => json}
                           itemToKey={(id) => id}
                           itemToString={(id) => id}
                           label="View Existing Camera Calibration"
                           placeholder="Select Camera Id"
                           onChange={onDropdownChange}/>
            <Heading as="h2" size="lg">Calibration Data</Heading>

            <Heading as="h3" size="md">Camera Matrix</Heading>
            {cameraCalibration && <MatrixDisplay matrix={cameraCalibration["camera_matrix"]}></MatrixDisplay>}

            <Heading as="h3" size="md">Rotation Vectors</Heading>
            {cameraCalibration && <MatrixDisplay matrix={cameraCalibration["rotation_vectors"]}></MatrixDisplay>}

            <Heading as="h3" size="md">Translation Vectors</Heading>
            {cameraCalibration && <MatrixDisplay matrix={cameraCalibration["translation_vectors"]}></MatrixDisplay>}

            <Heading as="h3" size="md">Distortion Coefficients</Heading>
            {cameraCalibration && <MatrixDisplay matrix={cameraCalibration["distortion_coefficients"]}></MatrixDisplay>}


            <Button onClick={calibrateCamera}>
            Compute Camera Calibration
            </Button>
        </VStack>
    </div>
  );
};

export default Calibration;