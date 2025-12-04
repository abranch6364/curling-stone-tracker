import React, { useState } from "react";
import "./ImageViewer.css";

import { useFilePicker } from 'use-file-picker';
import {
  FileAmountLimitValidator,
  FileTypeValidator,
  FileSizeValidator,
  ImageDimensionsValidator,
} from 'use-file-picker/validators';

const ImageViewer = () => {
  const [currentIndex, setCurrentIndex] = useState(0);

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


  const nextImage = () => {
    setCurrentIndex((prevIndex) => (prevIndex + 1) % filesContent.length);
  };
  const prevImage = () => {
    setCurrentIndex((prevIndex) => (prevIndex - 1 + filesContent.length) % filesContent.length);
  };

  const loadImage = () => {
    openFilePicker();
    setCurrentIndex(0);
  };

    if (errors.length) {
        return (
            <div>
                <button onClick={() => openFilePicker()}>Something went wrong, retry! </button>
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

    return (
        <div className="image-viewer">
            <button onClick={prevImage} className="nav-button">❮</button>
            <div className="image-stack">
                <img src={filesContent[currentIndex]?.content} alt={`Image ${currentIndex + 1}`} className="image" />
                <button onClick={loadImage}>Load Image</button>
            </div>
            <button onClick={nextImage} className="nav-button">❯</button>
        </div>
    );
};
export default ImageViewer;