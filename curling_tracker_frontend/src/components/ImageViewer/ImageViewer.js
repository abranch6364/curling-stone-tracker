import { useEffect, useState } from "react";
import { Button, Image as ChakraImage, FileUpload, Box, VStack } from "@chakra-ui/react"

const toURL = (file) => {
  if(typeof file === "string") {
    return file;
  }

  return URL.createObjectURL(file);
}


const ImageViewer = ({file, onFileChange, setImageDimensions, onImageClick, includeLoadButton}) => {
  const [localFile, setLocalFile] = useState(null);
  const [localImageDimensions, setLocalImageDimensions] = useState(null);

  const displayFile = file !== undefined ? file : localFile;

  //////////////////
  //Helper Functions
  //////////////////
  const updateDimensions = (imageURL) => {
    const img = new Image();
    img.onload = function() {
      setLocalImageDimensions({ height: this.height, width: this.width });
      if (setImageDimensions !== undefined) {
        setImageDimensions({ height: this.height, width: this.width });
      }
    };
    img.src = imageURL;
  }

  ///////////////
  //Use Functions
  ///////////////
  useEffect(() => {
    if(displayFile != null) {
      updateDimensions(toURL(displayFile));
    }
  }, [file]);

  ///////////
  //Callbacks
  ///////////
  const localOnFileChange = (details) => {
    if (onFileChange !== undefined) {
      onFileChange(details);
    } else {
      setLocalFile(details.acceptedFiles[0]);
      updateDimensions(toURL(details.acceptedFiles[0]));
    }
  };

  const imageClick = (e) => {
    var rect = e.target.getBoundingClientRect();
    var x_percent = (e.clientX - rect.left) / (rect.right - rect.left);
    var y_percent = (e.clientY - rect.top) / (rect.bottom - rect.top);

    var x = x_percent * localImageDimensions.width;
    var y = y_percent * localImageDimensions.height;
    if(onImageClick !== undefined) {
      onImageClick(x, y);
    }
  };

    return (
      <VStack align="center" justify="center">
        <Box>
          {displayFile ? <ChakraImage src={toURL(displayFile)} alt={`Image`} 
                                          onClick={imageClick} className="image"/> 
                                    : <Box bg="red" w="100%" h="100%" p="4" color="white">No image loaded yet</Box>}
        </Box>
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