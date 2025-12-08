import React, { useState } from "react";
import "./ImageViewer.css";

import { Button, Image } from "@chakra-ui/react"

import { useFilePicker } from 'use-file-picker';
import {
  FileAmountLimitValidator,
  FileTypeValidator,
  FileSizeValidator,
  ImageDimensionsValidator,
} from 'use-file-picker/validators';

const ImageViewer = ({onImageClick, setDimensions}) => {
  const { openFilePicker, filesContent, loading, errors } = useFilePicker({
    readAs: 'DataURL',
    accept: 'image/*',
    multiple: true,
    validators: [
      new FileAmountLimitValidator({ max: 1 }),
      new FileTypeValidator(['jpg', 'png']),
      new FileSizeValidator({ maxFileSize: 50 * 1024 * 1024 /* 50 MB */ }),
    ],
  });

  const loadImage = () => {
    openFilePicker();
  };

    if (errors.length) {
        return (
            <div>
                <Button onClick={() => openFilePicker()}>Something went wrong, retry! </Button>
                {errors.map(err => (
                <div>
                    {err.name}: {err.reason}
                </div>
            ))}
        </div>
    );
    }

    if (loading) {
        return <div>Loading...</div>;
    }

    const imageClick = (e) => {
      // e = Mouse click event.
      var rect = e.target.getBoundingClientRect();
      var x = e.clientX - rect.left; //x position within the element.
      var y = e.clientY - rect.top;  //y position within the element.
      onImageClick(x, y);
    };  

    const handleImageLoad = (e) => {
        const { naturalHeight, naturalWidth } = e.target;
        setDimensions({ height: naturalHeight, width: naturalWidth });
    };


    return (
        <div className="image-viewer">
            <div className="image-stack">
                {filesContent.length > 0 ? <Image src={filesContent[0]?.content} alt={`Image`} 
                                                onClick={imageClick} onLoad={handleImageLoad} className="image" /> 
                                         : <div>No Image Loaded...</div>}
                <Button onClick={loadImage}>Load Image</Button>
            </div>
        </div>
    );
};
export default ImageViewer;