import { useState, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { Stage, Layer, Rect, Circle, Line } from "react-konva";
import { VStack } from "@chakra-ui/react";
import { findInsertionPoint } from "../../utility/CurlingStoneHelper";

const fetchData = async () => {
  const response = await fetch("/api/sheet_coordinates");
  if (!response.ok) {
    throw new Error("Network response was not ok");
  }
  return response.json();
};

const CurlingSheetPlot = ({ plotTime, stones, sheetPlotXExtent, sheetPlotYExtent }) => {
  if (sheetPlotXExtent === undefined) {
    sheetPlotXExtent = [-8, 8];
  }

  if (sheetPlotYExtent === undefined) {
    sheetPlotYExtent = [35, 65];
  }
  let ratio = (sheetPlotXExtent[1] - sheetPlotXExtent[0]) / (sheetPlotYExtent[1] - sheetPlotYExtent[0]);

  const [sheetHeight, setSheetHeight] = useState(window.innerHeight * 0.6);
  const [sheetWidth, setSheetWidth] = useState(ratio * (window.innerHeight * 0.6));

  //////////////////
  //Helper Functions
  //////////////////
  const sheetToStageXCoordinate = (x) => {
    return (x - sheetPlotXExtent[0]) * (sheetWidth / (sheetPlotXExtent[1] - sheetPlotXExtent[0]));
  };

  const sheetToStageYCoordinate = (y) => {
    return sheetHeight - (y - sheetPlotYExtent[0]) * (sheetHeight / (sheetPlotYExtent[1] - sheetPlotYExtent[0]));
  };

  const sheetDistanceToStageDistance = (d) => {
    return d * (sheetWidth / (sheetPlotXExtent[1] - sheetPlotXExtent[0]));
  };

  const getStoneXPositionAtTime = (stone, current_time) => {
    if (stone.time_history[0] > current_time || stone.time_history[stone.time_history.length - 1] < current_time) {
      return null;
    }

    let index = findInsertionPoint(stone.time_history, current_time);

    if (index === 0) {
      return stone.position_history[index][0];
    }
    const t0 = stone.time_history[index - 1];
    const t1 = stone.time_history[index];
    const x0 = stone.position_history[index - 1][0];
    const x1 = stone.position_history[index][0];
    return x0 + ((x1 - x0) * (current_time - t0)) / (t1 - t0);
  };

  const getStoneYPositionAtTime = (stone, current_time) => {
    if (stone.time_history[0] > current_time || stone.time_history[stone.time_history.length - 1] < current_time) {
      return null;
    }

    let index = findInsertionPoint(stone.time_history, current_time);

    if (index === 0) {
      return stone.position_history[index][1];
    }

    const t0 = stone.time_history[index - 1];
    const t1 = stone.time_history[index];
    const y0 = stone.position_history[index - 1][1];
    const y1 = stone.position_history[index][1];

    return y0 + ((y1 - y0) * (current_time - t0)) / (t1 - t0);
  };

  const getStoneVisibilityAtTime = (stone, current_time) => {
    if (stone.time_history[0] > current_time || stone.time_history[stone.time_history.length - 1] < current_time) {
      return false;
    }

    return true;
  };

  const generateStonePathPoints = (stone, current_time) => {
    const pathPoints = [];
    for (let i = 0; i < stone.time_history.length; i++) {
      if (stone.time_history[i] <= current_time) {
        pathPoints.push(sheetToStageXCoordinate(stone.position_history[i][0]));
        pathPoints.push(sheetToStageYCoordinate(stone.position_history[i][1]));
      } else {
        break;
      }
    }

    // Add the interpolated current position as the last point
    if (pathPoints.length > 0) {
      pathPoints.push(sheetToStageXCoordinate(getStoneXPositionAtTime(stone, current_time)));
      pathPoints.push(sheetToStageYCoordinate(getStoneYPositionAtTime(stone, current_time)));
    }
    return pathPoints;
  };

  ///////////////
  //Use Functions
  ///////////////
  const { data, error, isLoading } = useQuery({
    queryKey: ["/api/sheet_coordinates"],
    queryFn: () => fetchData(),
  });

  useEffect(() => {
    function handleResize() {
      setSheetHeight(window.innerHeight * 0.6);
      setSheetWidth(ratio * (window.innerHeight * 0.6));
    }

    // Add event listener for window resize
    window.addEventListener("resize", handleResize);

    // Cleanup function to remove the event listener
    return () => window.removeEventListener("resize", handleResize);
  }, []); // Empty dependency array means this effect runs once on mount and once on unmount

  return (
    <VStack>
      <Stage width={sheetWidth} height={sheetHeight} backgroundColor="white">
        <Layer>
          <Rect x={0} y={0} width={sheetWidth} height={sheetHeight} fill="white" />
        </Layer>

        {["away", "home"].map((side, index) => (
          <Layer>
            <Circle
              x={data ? sheetToStageXCoordinate(data[side + "_pin"][0]) : 0}
              y={data ? sheetToStageYCoordinate(data[side + "_pin"][1]) : 0}
              radius={sheetDistanceToStageDistance(6)}
              fill="blue"
            />

            <Circle
              x={data ? sheetToStageXCoordinate(data[side + "_pin"][0]) : 0}
              y={data ? sheetToStageYCoordinate(data[side + "_pin"][1]) : 0}
              radius={sheetDistanceToStageDistance(4)}
              fill="white"
            />

            <Circle
              x={data ? sheetToStageXCoordinate(data[side + "_pin"][0]) : 0}
              y={data ? sheetToStageYCoordinate(data[side + "_pin"][1]) : 0}
              radius={sheetDistanceToStageDistance(2)}
              fill="red"
            />

            <Circle
              x={data ? sheetToStageXCoordinate(data[side + "_pin"][0]) : 0}
              y={data ? sheetToStageYCoordinate(data[side + "_pin"][1]) : 0}
              radius={sheetDistanceToStageDistance(0.5)}
              fill="white"
            />

            <Line
              points={[
                data ? sheetToStageXCoordinate(data[side + "_left_hog"][0]) : 0,
                data ? sheetToStageYCoordinate(data[side + "_left_tee_12"][1]) : 0,
                data ? sheetToStageXCoordinate(data[side + "_right_hog"][0]) : 0,
                data ? sheetToStageYCoordinate(data[side + "_right_tee_12"][1]) : 0,
              ]}
              stroke="black"
              strokeWidth={1}
            />

            <Line
              points={[
                data ? sheetToStageXCoordinate(data[side + "_left_hog"][0]) : 0,
                data ? sheetToStageYCoordinate(data[side + "_left_backline_corner"][1]) : 0,
                data ? sheetToStageXCoordinate(data[side + "_right_hog"][0]) : 0,
                data ? sheetToStageYCoordinate(data[side + "_right_backline_corner"][1]) : 0,
              ]}
              stroke="black"
              strokeWidth={1}
            />

            <Line
              points={[
                data ? sheetToStageXCoordinate(data[side + "_left_hog"][0]) : 0,
                data
                  ? sheetToStageYCoordinate(data[side + "_left_hog"][1]) +
                    (side === "away" ? sheetDistanceToStageDistance(0.4) : -sheetDistanceToStageDistance(0.4))
                  : 0,
                data ? sheetToStageXCoordinate(data[side + "_right_hog"][0]) : 0,
                data
                  ? sheetToStageYCoordinate(data[side + "_right_hog"][1]) +
                    (side === "away" ? sheetDistanceToStageDistance(0.4) : -sheetDistanceToStageDistance(0.4))
                  : 0,
              ]}
              stroke="black"
              strokeWidth={sheetDistanceToStageDistance(0.4)}
            />
          </Layer>
        ))}

        <Layer>
          <Line
            points={[
              data ? sheetToStageXCoordinate(data["away_back_center_12"][0]) : 0,
              data ? sheetToStageYCoordinate(data["away_back_center_12"][1]) : 0,
              data ? sheetToStageXCoordinate(data["home_back_center_12"][0]) : 0,
              data ? sheetToStageYCoordinate(data["home_back_center_12"][1]) : 0,
            ]}
            stroke="black"
            strokeWidth={1}
          />

          <Line
            points={[
              data ? sheetToStageXCoordinate(data["away_left_backline_corner"][0]) : 0,
              data ? sheetToStageYCoordinate(data["away_left_backline_corner"][1]) : 0,
              data ? sheetToStageXCoordinate(data["home_left_backline_corner"][0]) : 0,
              data ? sheetToStageYCoordinate(data["home_left_backline_corner"][1]) : 0,
            ]}
            stroke="black"
            strokeWidth={1}
          />

          <Line
            points={[
              data ? sheetToStageXCoordinate(data["away_right_backline_corner"][0]) : 0,
              data ? sheetToStageYCoordinate(data["away_right_backline_corner"][1]) : 0,
              data ? sheetToStageXCoordinate(data["home_right_backline_corner"][0]) : 0,
              data ? sheetToStageYCoordinate(data["home_right_backline_corner"][1]) : 0,
            ]}
            stroke="black"
            strokeWidth={1}
          />
        </Layer>

        <Layer>
          {stones &&
            stones.map((stone, index) => {
              if (!getStoneVisibilityAtTime(stone, plotTime)) return null;

              const pathPoints = generateStonePathPoints(stone, plotTime);

              return pathPoints.length > 2 ? (
                <Line key={`path-${index}`} points={pathPoints} stroke={stone.color} strokeWidth={4} opacity={0.75} />
              ) : null;
            })}
        </Layer>
        <Layer>
          {stones &&
            stones.map(
              (stone, index) =>
                getStoneVisibilityAtTime(stone, plotTime) && (
                  <Circle
                    x={sheetToStageXCoordinate(getStoneXPositionAtTime(stone, plotTime))}
                    y={sheetToStageYCoordinate(getStoneYPositionAtTime(stone, plotTime))}
                    radius={sheetDistanceToStageDistance(0.5)}
                    fill={stone.color}
                  />
                ),
            )}
        </Layer>
      </Stage>
    </VStack>
  );
};

export default CurlingSheetPlot;
