import logo from './logo.svg';
import './App.css';
import './Calibration.css';

import { useEffect, useState, useRef } from 'react';
import ImageViewer from "./components/ImageViewer/ImageViewer";
import MatrixDisplay from './components/MatrixDisplay/MatrixDisplay';

const App = () => {
  const [sheetCoords, setSheetCoords] = useState({});
  const [imageCoords, setImageCoords] = useState({});
  const [selectedKey, setSelectedKey] = useState('');
  const [cameraCalibration, setCameraCalibration] = useState(null);
  const inputRefs = useRef({})
  const [imageDimensions, setImageDimensions] = useState({ height: 0, width: 0 });

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
    <div className="App">
      <div className="CalibrationContainer">
        <ImageViewer onImageClick={imageViewerClick} setDimensions={setImageDimensions}/>
        <div className="PointList">
          {Object.keys(sheetCoords).map((key) => (
            <div key={key}>
              <strong>{key}:</strong>
              <input
                type="text"
                ref={el => inputRefs.current[key] = el}
                value={imageCoords[key]}
                onChange={(e) => inputHandleChange(e, key)}
                onFocus={() => setSelectedKey(key)}
              />
            </div>
          ))}
        </div>
        <div className="CalibrationMatrix">
          <h2>Calibration Data</h2>

          <h3>Camera Matrix</h3>
          {cameraCalibration && <MatrixDisplay matrix={cameraCalibration["camera_matrix"]}></MatrixDisplay>}
  
          <h3>Rotation Vectors</h3>
          {cameraCalibration && <MatrixDisplay matrix={cameraCalibration["rotation_vectors"]}></MatrixDisplay>}

          <h3>Translation Vectors</h3>
          {cameraCalibration && <MatrixDisplay matrix={cameraCalibration["translation_vectors"]}></MatrixDisplay>}

          <h3>Distortion Coefficients</h3>
          {cameraCalibration && <MatrixDisplay matrix={cameraCalibration["distortion_coefficients"]}></MatrixDisplay>}


          <button onClick={calibrateCamera}>
            Compute Camera Calibration
          </button>
        </div>
      </div>
    </div>
  );
};

export default App;
