import React, { useState, useEffect, useRef } from "react";
import "./Calibration.css";

import { Button, Input, HStack, VStack, Text, Heading } from "@chakra-ui/react"

import ImageViewer from "../ImageViewer/ImageViewer";
import MatrixDisplay from '../MatrixDisplay/MatrixDisplay';
import { useQueryClient } from '@tanstack/react-query';


const Calibration = ({cameraCalibration, setCameraId}) => {

    const [sheetCoords, setSheetCoords] = useState({});
    const [imageCoords, setImageCoords] = useState({});
    const [selectedKey, setSelectedKey] = useState('');
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
        .then(json => {
          setCameraId(json["camera_id"]);
          queryClient.invalidateQueries({ queryKey: ['/api/camera_ids'] });
        })
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
    <HStack>
        <ImageViewer onImageClick={imageViewerClick} 
                     onImageLoad={(e) => setImageDimensions({ height: e.target.naturalHeight, width: e.target.naturalWidth })}
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
    </HStack>
  );
};

export default Calibration;