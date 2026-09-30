import { useEffect, useState } from "react";
import { Button, Image as ChakraImage, FileUpload, Box, VStack, Text } from "@chakra-ui/react";

const toURL = (file) => {
  if (typeof file === "string") {
    return file;
  }
  return URL.createObjectURL(file);
};

const ImageViewer = ({
  file,
  onFileChange,
  onImageDimensionChange,
  onImageClick,
  includeLoadButton,
  encodingType = "",
  placeholderHint = "Load an image to get started",
}) => {
  const [localFile, setLocalFile] = useState(null);
  const [localImageDimensions, setLocalImageDimensions] = useState(null);

  const displayFile = file !== undefined ? file : localFile;

  //////////////////
  //Helper Functions
  //////////////////
  const updateDimensions = (imageURL) => {
    const img = new Image();
    img.onload = function () {
      setLocalImageDimensions({ height: this.height, width: this.width });

      if (onImageDimensionChange !== undefined) {
        onImageDimensionChange({ height: this.height, width: this.width });
      }
    };
    img.src = `${encodingType}${imageURL}`;
  };

  ///////////////
  //Use Functions
  ///////////////
  useEffect(() => {
    if (displayFile != null) {
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
    if (onImageClick !== undefined) {
      onImageClick(x, y);
    }
  };

  return (
    <VStack align="center" justify="center">
      <Box>
        {displayFile ? (
          <ChakraImage
            src={`${encodingType}${toURL(displayFile)}`}
            alt={`Image`}
            onClick={imageClick}
            className="image"
          />
        ) : (
          <VStack
            justify="center"
            gap="2"
            minW="320px"
            minH="240px"
            p="6"
            borderWidth="2px"
            borderStyle="dashed"
            borderColor="border"
            borderRadius="md"
            bg="bg.subtle"
            color="fg.muted"
          >
            <svg
              width="40"
              height="40"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <circle cx="9" cy="9" r="2" />
              <path d="m21 15-3.1-3.1a2 2 0 0 0-2.8 0L6 21" />
            </svg>
            <Text fontWeight="medium">No image loaded</Text>
            <Text fontSize="sm">{placeholderHint}</Text>
          </VStack>
        )}
      </Box>
      {includeLoadButton && (
        <FileUpload.Root onFileChange={localOnFileChange} align="center">
          <FileUpload.HiddenInput />
          <FileUpload.Trigger asChild>
            <Box w="100%" display="flex" justifyContent="center">
              <Button>Load Image</Button>
            </Box>
          </FileUpload.Trigger>
        </FileUpload.Root>
      )}
    </VStack>
  );
};
export default ImageViewer;
