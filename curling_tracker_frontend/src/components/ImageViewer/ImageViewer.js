import React, { useState } from "react";
import "./ImageViewer.css";

import { Button, Image, FileUpload, Box, VStack } from "@chakra-ui/react"

const ImageViewer = ({file, onFileChange, onImageClick, onImageLoad}) => {
  const [localFile, setLocalFile] = useState(null);

  const displayFile = file !== undefined ? file : localFile

  const localOnFileChange = (details) => {
    if (onFileChange !== undefined) {
      onFileChange(details);
    } else {
      setLocalFile(details.acceptedFiles[0]);
    }
  };

    const imageClick = (e) => {
      var rect = e.target.getBoundingClientRect();
      var x = e.clientX - rect.left;
      var y = e.clientY - rect.top;
      onImageClick(x, y);
    };  

    return (
      <VStack align="center" justify="center">
          {displayFile ? <Image src={URL.createObjectURL(displayFile)} alt={`Image`} 
                                          onClick={imageClick} onLoad={onImageLoad} className="image" /> 
                                    : <Box bg="red" w="100%" h="100%" p="4" color="white">No image loaded yet</Box>}      
          
            <FileUpload.Root onFileChange={localOnFileChange} align="center">
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
    );
};
export default ImageViewer;