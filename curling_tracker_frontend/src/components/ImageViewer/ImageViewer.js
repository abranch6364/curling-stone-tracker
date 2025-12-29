import React, { useState } from "react";
import "./ImageViewer.css";

import { Button, Image, FileUpload, Box, VStack } from "@chakra-ui/react"

const ImageViewer = ({file, onFileChange, onImageClick, onImageLoad, includeLoadButton}) => {
  const [localFile, setLocalFile] = useState(null);
  const [imageDimensions, setImageDimensions] = useState(null);

  const displayFile = file !== undefined ? file : localFile

  const localOnFileChange = (details) => {
    if (onFileChange !== undefined) {
      onFileChange(details);
    } else {
      setLocalFile(details.acceptedFiles[0]);
    }
  };

  const localOnImageLoad = (e) => {
    setImageDimensions({ height: e.target.naturalHeight, width: e.target.naturalWidth });
    if (onImageLoad !== undefined) {
      onImageLoad(e);
    }

  };

  const imageClick = (e) => {
    var rect = e.target.getBoundingClientRect();
    var x_percent = (e.clientX - rect.left) / (rect.right - rect.left);
    var y_percent = (e.clientY - rect.top) / (rect.bottom - rect.top);

    var x = x_percent * imageDimensions.width;
    var y = y_percent * imageDimensions.height;
    if(onImageClick !== undefined) {
      onImageClick(x, y);
    }
  };



    return (
      <VStack align="center" justify="center">
          {displayFile ? <Image src={URL.createObjectURL(displayFile)} alt={`Image`} 
                                          onClick={imageClick} onLoad={localOnImageLoad} className="image" /> 
                                    : <Box bg="red" w="100%" h="100%" p="4" color="white">No image loaded yet</Box>} 

          {includeLoadButton && <FileUpload.Root onFileChange={localOnFileChange} align="center">
              <FileUpload.HiddenInput />
              <FileUpload.Trigger asChild>
                <Box w="100%" display="flex" justifyContent="center">
                  <Button>
                    Load Image
                  </Button>
                </Box>
              </FileUpload.Trigger>
            </FileUpload.Root>}     
      </VStack>
    );
};
export default ImageViewer;