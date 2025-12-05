import logo from './logo.svg';
import './App.css';
import './Calibration.css';

import { useEffect, useState, useRef } from 'react';
import ImageViewer from "./components/ImageViewer/ImageViewer";

const App = () => {
  const [sheetCoords, setSheetCoords] = useState({});
  const [imageCoords, setImageCoords] = useState({});
  const [selectedKey, setSelectedKey] = useState('');
  const inputRefs = useRef({})

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
        <ImageViewer onImageClick={imageViewerClick} />
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
      </div>
    </div>
  );
};

export default App;
