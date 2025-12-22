import React, { useState, useEffect, useRef } from "react";
import { useQuery } from '@tanstack/react-query';

import { Stage, Layer, Rect, Circle, Line } from 'react-konva';


const CurlingSheetPlot = ({stones}) => {
  let sheetPlotXExtent = [-8, 8];
  let sheetPlotYExtent = [35, 65];
  let ratio = (sheetPlotXExtent[1] - sheetPlotXExtent[0]) / (sheetPlotYExtent[1] - sheetPlotYExtent[0]);

  const [sheetHeight, setSheetHeight] = useState(window.innerHeight / 1.25);
  const [sheetWidth, setSheetWidth] = useState(ratio * sheetHeight);

  useEffect(() => {
    function handleResize() {
      setSheetHeight(window.innerHeight / 1.25);
      setSheetWidth(ratio * sheetHeight);
    }

    // Add event listener for window resize
    window.addEventListener('resize', handleResize);

    // Cleanup function to remove the event listener
    return () => window.removeEventListener('resize', handleResize);
  }, []); // Empty dependency array means this effect runs once on mount and once on unmount

  const sheetToStageXCoordinate = (x) => {
    return (x - sheetPlotXExtent[0]) * (sheetWidth / (sheetPlotXExtent[1] - sheetPlotXExtent[0]));
  };

  const sheetToStageYCoordinate = (y) => {
    return sheetHeight - ((y - sheetPlotYExtent[0]) * (sheetHeight / (sheetPlotYExtent[1] - sheetPlotYExtent[0])));
  };

  const sheetDistanceToStageDistance = (d) => {
    return d * (sheetWidth / (sheetPlotXExtent[1] - sheetPlotXExtent[0]));
  }

      const fetchData = async () => {
        const response = await fetch('/api/sheet_coordinates');
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    }

    const { data, error, isLoading } = useQuery({
                                queryKey: ['/api/sheet_coordinates'],
                                queryFn: () => fetchData()
                            });


  return (
    <Stage width={sheetWidth} height={sheetHeight} backgroundColor="white">
      <Layer>
        <Rect
          x={0}
          y={0}
          width={sheetWidth}
          height={sheetHeight}
          fill="white"
        />
      </Layer>

      {["side_a", "side_b"].map((side, index) => (
        
        <Layer>

          <Circle
            x={data ? sheetToStageXCoordinate(data[side]['pin'][0]) : 0}
            y={data ? sheetToStageYCoordinate(data[side]['pin'][1]) : 0}
            radius={sheetDistanceToStageDistance(6)}
            fill="blue"
          />

          <Circle
            x={data ? sheetToStageXCoordinate(data[side]['pin'][0]) : 0}
            y={data ? sheetToStageYCoordinate(data[side]['pin'][1]) : 0}
            radius={sheetDistanceToStageDistance(4)}
            fill="white"
          />

          <Circle
            x={data ? sheetToStageXCoordinate(data[side]['pin'][0]) : 0}
            y={data ? sheetToStageYCoordinate(data[side]['pin'][1]) : 0}
            radius={sheetDistanceToStageDistance(2)}
            fill="red"
          />

          <Circle
            x={data ? sheetToStageXCoordinate(data[side]['pin'][0]) : 0}
            y={data ? sheetToStageYCoordinate(data[side]['pin'][1]) : 0}
            radius={sheetDistanceToStageDistance(0.5)}
            fill="white"
          />

          <Line
            points={[data ? sheetToStageXCoordinate(data[side]['left_hog'][0]) : 0, data ? sheetToStageYCoordinate(data[side]['left_tee_12'][1]) : 0,
                    data ? sheetToStageXCoordinate(data[side]['right_hog'][0]) : 0, data ? sheetToStageYCoordinate(data[side]['right_tee_12'][1]) : 0]}
            stroke="black"
            strokeWidth={1}
          />

          <Line
            points={[data ? sheetToStageXCoordinate(data[side]['left_hog'][0]) : 0, data ? sheetToStageYCoordinate(data[side]['left_backline_corner'][1]) : 0,
                    data ? sheetToStageXCoordinate(data[side]['right_hog'][0]) : 0, data ? sheetToStageYCoordinate(data[side]['right_backline_corner'][1]) : 0]}
            stroke="black"
            strokeWidth={1}
          />

          <Line
            points={[data ? sheetToStageXCoordinate(data[side]['left_hog'][0]) : 0, data ? sheetToStageYCoordinate(data[side]['left_hog'][1]) + (side === "side_a" ? sheetDistanceToStageDistance(0.4) : -sheetDistanceToStageDistance(0.4)) : 0,
                    data ? sheetToStageXCoordinate(data[side]['right_hog'][0]) : 0, data ? sheetToStageYCoordinate(data[side]['right_hog'][1]) + (side === "side_a" ? sheetDistanceToStageDistance(0.4) : -sheetDistanceToStageDistance(0.4)) : 0]}
            stroke="black"
            strokeWidth={sheetDistanceToStageDistance(0.4)}
          />
        </Layer>
      ))}

      <Layer>
        <Line
          points={[data ? sheetToStageXCoordinate(data["side_a"]['back_center_12'][0]) : 0, data ? sheetToStageYCoordinate(data["side_a"]['back_center_12'][1]) : 0,
                   data ? sheetToStageXCoordinate(data["side_b"]['back_center_12'][0]) : 0, data ? sheetToStageYCoordinate(data["side_b"]['back_center_12'][1]) : 0]}
          stroke="black"
          strokeWidth={1}
        />  

        <Line
          points={[data ? sheetToStageXCoordinate(data["side_a"]['left_backline_corner'][0]) : 0, data ? sheetToStageYCoordinate(data["side_a"]['left_backline_corner'][1]) : 0,
                   data ? sheetToStageXCoordinate(data["side_b"]['left_backline_corner'][0]) : 0, data ? sheetToStageYCoordinate(data["side_b"]['left_backline_corner'][1]) : 0]}
          stroke="black"
          strokeWidth={1}
        />  

        <Line
          points={[data ? sheetToStageXCoordinate(data["side_a"]['right_backline_corner'][0]) : 0, data ? sheetToStageYCoordinate(data["side_a"]['right_backline_corner'][1]) : 0,
                   data ? sheetToStageXCoordinate(data["side_b"]['right_backline_corner'][0]) : 0, data ? sheetToStageYCoordinate(data["side_b"]['right_backline_corner'][1]) : 0]}
          stroke="black"
          strokeWidth={1}
        />  
      </Layer>

      <Layer>
        {stones && stones.map((stone, index) => (
          <Circle
            x={sheetToStageXCoordinate(stone.sheet_coords[0])}
            y={sheetToStageYCoordinate(stone.sheet_coords[1])}
            radius={sheetDistanceToStageDistance(0.5)}
            fill={stone.color}
          />
        ))}
      </Layer>
    </Stage>

  );
};

export default CurlingSheetPlot;