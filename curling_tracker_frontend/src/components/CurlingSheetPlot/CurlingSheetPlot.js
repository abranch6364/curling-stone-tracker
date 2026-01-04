import { useState, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { Stage, Layer, Rect, Circle, Line } from "react-konva";
import { VStack, HStack, Slider, Button } from "@chakra-ui/react";

const fetchData = async () => {
  const response = await fetch("/api/sheet_coordinates");
  if (!response.ok) {
    throw new Error("Network response was not ok");
  }
  return response.json();
};

/**
 * Finds the index where the target should be inserted to maintain sorted order.
 * Assumes the input array `nums` is sorted in ascending order.
 * @param {number[]} nums - The sorted array.
 * @param {number} target - The value to insert.
 * @returns {number} The insertion index.
 */
function findInsertionPoint(nums, target) {
  let left = 0;
  let right = nums.length - 1; // Use a closed interval [left, right]

  while (left <= right) {
    // Calculate the middle index
    const mid = Math.floor((left + right) / 2);

    if (nums[mid] < target) {
      // Target is in the right half, update the left boundary
      left = mid + 1;
    } else if (nums[mid] > target) {
      // Target is in the left half, update the right boundary
      right = mid - 1;
    } else {
      // If the target is found, return that index (for the leftmost occurrence)
      return mid;
    }
  }

  // If the loop finishes without finding the target, 'left' points to
  // the correct insertion point (the index of the first element greater than target).
  return left;
}

const CurlingSheetPlot = ({ stones, sheetPlotXExtent, sheetPlotYExtent }) => {
  if (sheetPlotXExtent === undefined) {
    sheetPlotXExtent = [-8, 8];
  }

  if (sheetPlotYExtent === undefined) {
    sheetPlotYExtent = [35, 65];
  }
  let ratio = (sheetPlotXExtent[1] - sheetPlotXExtent[0]) / (sheetPlotYExtent[1] - sheetPlotYExtent[0]);

  const [sheetHeight, setSheetHeight] = useState(window.innerHeight * 0.7);
  const [sheetWidth, setSheetWidth] = useState(ratio * sheetHeight);
  const [plotTime, setPlotTime] = useState(0);
  const [animationRunning, setAnimationRunning] = useState(false);
  const intervalRef = useRef(null); // Ref to store the interval ID

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

  const getStoneMinTime = (stones) => {
    if (!stones || stones.length === 0) {
      return 0;
    }

    let minTime = Infinity;
    for (const stone of stones) {
      for (const t of stone.time_history) {
        if (t < minTime) {
          minTime = t;
        }
      }
    }
    return minTime;
  };

  const getStoneMaxTime = (stones) => {
    if (!stones || stones.length === 0) {
      return 0;
    }

    let maxTime = -Infinity;
    for (const stone of stones) {
      for (const t of stone.time_history) {
        if (t > maxTime) {
          maxTime = t;
        }
      }
    }
    return maxTime;
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

  ///////////////
  //Use Functions
  ///////////////
  const { data, error, isLoading } = useQuery({
    queryKey: ["/api/sheet_coordinates"],
    queryFn: () => fetchData(),
  });

  useEffect(() => {
    function handleResize() {
      setSheetHeight(window.innerHeight / 1.25);
      setSheetWidth(ratio * sheetHeight);
    }

    // Add event listener for window resize
    window.addEventListener("resize", handleResize);

    // Cleanup function to remove the event listener
    return () => window.removeEventListener("resize", handleResize);
  }, []); // Empty dependency array means this effect runs once on mount and once on unmount

  ///////////
  //Callbacks
  ///////////

  const onPlayToggle = () => {
    if (animationRunning) {
      setAnimationRunning(false);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    } else {
      setAnimationRunning(true);
      const startTime = Date.now();
      const startPlotTime = plotTime;

      intervalRef.current = setInterval(() => {
        const elapsed = (Date.now() - startTime) / 1000; // Convert to seconds
        const newPlotTime = startPlotTime + elapsed;

        if (newPlotTime >= getStoneMaxTime(stones)) {
          setPlotTime(getStoneMaxTime(stones));
          setAnimationRunning(false);
          clearInterval(intervalRef.current);
        } else {
          setPlotTime(newPlotTime);
        }
      }, 50); // Update every 50ms for smooth animation
    }
  };

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
            stones.map(
              (stone, index) =>
                getStoneVisibilityAtTime(stone, plotTime) && (
                  <Circle
                    x={sheetToStageXCoordinate(getStoneXPositionAtTime(stone, plotTime))}
                    y={sheetToStageYCoordinate(getStoneYPositionAtTime(stone, plotTime))}
                    radius={sheetDistanceToStageDistance(0.5)}
                    fill={stone.color}
                  />
                )
            )}
        </Layer>
      </Stage>
      <Slider.Root
        width="100%"
        min={getStoneMinTime(stones)}
        max={getStoneMaxTime(stones)}
        step={0.25}
        onValueChange={(e) => setPlotTime(e.value[0])}
        value={[plotTime]}
      >
        <HStack justify="space-between">
          <Slider.Label>Time</Slider.Label>
          <Slider.ValueText />
        </HStack>
        <Slider.Control>
          <Slider.Track>
            <Slider.Range />
          </Slider.Track>
          <Slider.Thumbs />
        </Slider.Control>
      </Slider.Root>
      <HStack>
        <Button onClick={onPlayToggle}>{animationRunning ? "Pause" : "Play"}</Button>
      </HStack>
    </VStack>
  );
};

export default CurlingSheetPlot;
