import React, { useState } from "react";
import "./ImageViewer.css";

import { Button, Image, FileUpload, Box } from "@chakra-ui/react"

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
        <div className="image-viewer">
            <div className="image-stack">
                {displayFile ? <Image src={URL.createObjectURL(displayFile)} alt={`Image`} 
                                                onClick={imageClick} onLoad={onImageLoad} className="image" /> 
                                         : <Box bg="red" w="100%" h="100%" p="4" color="white">No image loaded yet</Box>}      
                <FileUpload.Root onFileChange={localOnFileChange}>
                  <FileUpload.HiddenInput />
                  <FileUpload.Trigger asChild>
                    <Button>
                      Load Image
                    </Button>
                  </FileUpload.Trigger>
                </FileUpload.Root>

            </div>
        </div>
    );
};
export default ImageViewer;