import  { useState, useEffect } from "react";
import { useQuery } from '@tanstack/react-query';
import { Stage, Layer, Rect, Circle, Line } from 'react-konva';

const fetchData = async () => {
  const response = await fetch('/api/sheet_coordinates');
  if (!response.ok) {
      throw new Error('Network response was not ok');
  }
  return response.json();
}

const CurlingSheetPlot = ({stones, sheetPlotXExtent, sheetPlotYExtent}) => {
  if (sheetPlotXExtent === undefined) {
    sheetPlotXExtent = [-8, 8];
  }

  if (sheetPlotXExtent === undefined) {
    sheetPlotYExtent = [35, 65];
  }
  let ratio = (sheetPlotXExtent[1] - sheetPlotXExtent[0]) / (sheetPlotYExtent[1] - sheetPlotYExtent[0]);

  const [sheetHeight, setSheetHeight] = useState(window.innerHeight / 1.25);
  const [sheetWidth, setSheetWidth] = useState(ratio * sheetHeight);

  //////////////////
  //Helper Functions
  //////////////////
  const sheetToStageXCoordinate = (x) => {
    return (x - sheetPlotXExtent[0]) * (sheetWidth / (sheetPlotXExtent[1] - sheetPlotXExtent[0]));
  };

  const sheetToStageYCoordinate = (y) => {
    return sheetHeight - ((y - sheetPlotYExtent[0]) * (sheetHeight / (sheetPlotYExtent[1] - sheetPlotYExtent[0])));
  };

  const sheetDistanceToStageDistance = (d) => {
    return d * (sheetWidth / (sheetPlotXExtent[1] - sheetPlotXExtent[0]));
  }
  
  ///////////////
  //Use Functions
  ///////////////
  const { data, error, isLoading } = useQuery({
                              queryKey: ['/api/sheet_coordinates'],
                              queryFn: () => fetchData()
                          });
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

      {["away", "home"].map((side, index) => (
        
        <Layer>

          <Circle
            x={data ? sheetToStageXCoordinate(data[side + '_pin'][0]) : 0}
            y={data ? sheetToStageYCoordinate(data[side + '_pin'][1]) : 0}
            radius={sheetDistanceToStageDistance(6)}
            fill="blue"
          />

          <Circle
            x={data ? sheetToStageXCoordinate(data[side + '_pin'][0]) : 0}
            y={data ? sheetToStageYCoordinate(data[side + '_pin'][1]) : 0}
            radius={sheetDistanceToStageDistance(4)}
            fill="white"
          />

          <Circle
            x={data ? sheetToStageXCoordinate(data[side + '_pin'][0]) : 0}
            y={data ? sheetToStageYCoordinate(data[side + '_pin'][1]) : 0}
            radius={sheetDistanceToStageDistance(2)}
            fill="red"
          />

          <Circle
            x={data ? sheetToStageXCoordinate(data[side + '_pin'][0]) : 0}
            y={data ? sheetToStageYCoordinate(data[side + '_pin'][1]) : 0}
            radius={sheetDistanceToStageDistance(0.5)}
            fill="white"
          />

          <Line
            points={[data ? sheetToStageXCoordinate(data[side + '_left_hog'][0]) : 0, data ? sheetToStageYCoordinate(data[side + '_left_tee_12'][1]) : 0,
                    data ? sheetToStageXCoordinate(data[side + '_right_hog'][0]) : 0, data ? sheetToStageYCoordinate(data[side + '_right_tee_12'][1]) : 0]}
            stroke="black"
            strokeWidth={1}
          />

          <Line
            points={[data ? sheetToStageXCoordinate(data[side + '_left_hog'][0]) : 0, data ? sheetToStageYCoordinate(data[side + '_left_backline_corner'][1]) : 0,
                    data ? sheetToStageXCoordinate(data[side + '_right_hog'][0]) : 0, data ? sheetToStageYCoordinate(data[side + '_right_backline_corner'][1]) : 0]}
            stroke="black"
            strokeWidth={1}
          />

          <Line
            points={[data ? sheetToStageXCoordinate(data[side + '_left_hog'][0]) : 0, data ? sheetToStageYCoordinate(data[side + '_left_hog'][1]) + (side === "away" ? sheetDistanceToStageDistance(0.4) : -sheetDistanceToStageDistance(0.4)) : 0,
                    data ? sheetToStageXCoordinate(data[side + '_right_hog'][0]) : 0, data ? sheetToStageYCoordinate(data[side + '_right_hog'][1]) + (side === "away" ? sheetDistanceToStageDistance(0.4) : -sheetDistanceToStageDistance(0.4)) : 0]}
            stroke="black"
            strokeWidth={sheetDistanceToStageDistance(0.4)}
          />
        </Layer>
      ))}

      <Layer>
        <Line
          points={[data ? sheetToStageXCoordinate(data['away_back_center_12'][0]) : 0, data ? sheetToStageYCoordinate(data['away_back_center_12'][1]) : 0,
                   data ? sheetToStageXCoordinate(data['home_back_center_12'][0]) : 0, data ? sheetToStageYCoordinate(data['home_back_center_12'][1]) : 0]}
          stroke="black"
          strokeWidth={1}
        />  

        <Line
          points={[data ? sheetToStageXCoordinate(data['away_left_backline_corner'][0]) : 0, data ? sheetToStageYCoordinate(data['away_left_backline_corner'][1]) : 0,
                   data ? sheetToStageXCoordinate(data['home_left_backline_corner'][0]) : 0, data ? sheetToStageYCoordinate(data['home_left_backline_corner'][1]) : 0]}
          stroke="black"
          strokeWidth={1}
        />  

        <Line
          points={[data ? sheetToStageXCoordinate(data['away_right_backline_corner'][0]) : 0, data ? sheetToStageYCoordinate(data['away_right_backline_corner'][1]) : 0,
                   data ? sheetToStageXCoordinate(data['home_right_backline_corner'][0]) : 0, data ? sheetToStageYCoordinate(data['home_right_backline_corner'][1]) : 0]}
          stroke="black"
          strokeWidth={1}
        />  
      </Layer>

      <Layer>
        {stones && stones.map((stone, index) => (
          <Circle
            x={sheetToStageXCoordinate(stone.sheet_coordinates[0])}
            y={sheetToStageYCoordinate(stone.sheet_coordinates[1])}
            radius={sheetDistanceToStageDistance(0.5)}
            fill={stone.color}
          />
        ))}
      </Layer>
    </Stage>

  );
};

export default CurlingSheetPlot;