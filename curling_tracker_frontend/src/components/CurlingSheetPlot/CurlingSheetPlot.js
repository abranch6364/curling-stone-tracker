import { useState, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { Stage, Layer, Rect, Circle, Line, Ellipse } from "react-konva";
import { Box } from "@chakra-ui/react";
import { findInsertionPoint } from "../../utility/CurlingStoneHelper";

// Chi-squared value for a 95% region of a 2D Gaussian
const CHI_SQUARED_95 = 5.991;
// Draw an uncertainty ellipse along a stone's path every this many history samples
const PATH_ELLIPSE_INTERVAL = 5;
// Darker versions of the stone colours as [r, g, b], so ellipses stand out on the white sheet
const ELLIPSE_COLORS = {
  yellow: [150, 110, 0],
  green: [0, 100, 0],
  red: [139, 0, 0],
  blue: [0, 0, 139],
};
const ellipseColor = (stoneColor, alpha) => {
  const [r, g, b] = ELLIPSE_COLORS[stoneColor] ?? [0, 0, 0];
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

const fetchData = async () => {
  const response = await fetch("/api/calibration_coordinates");
  if (!response.ok) {
    throw new Error("Network response was not ok");
  }
  return response.json();
};

// orientation "vertical" draws the sheet with away at the top, sized to the window height.
// orientation "horizontal" draws it with home on the left and away on the right, sized to the width of its container.
const CurlingSheetPlot = ({
  plotTime,
  stones,
  sheetPlotXExtent,
  sheetPlotYExtent,
  orientation = "vertical",
  showUncertainty = false,
}) => {
  if (sheetPlotXExtent === undefined) {
    sheetPlotXExtent = [-8, 8];
  }

  if (sheetPlotYExtent === undefined) {
    sheetPlotYExtent = [35, 65];
  }
  const isHorizontal = orientation === "horizontal";
  const xSpan = sheetPlotXExtent[1] - sheetPlotXExtent[0];
  const ySpan = sheetPlotYExtent[1] - sheetPlotYExtent[0];

  const [windowHeight, setWindowHeight] = useState(window.innerHeight);
  const [containerWidth, setContainerWidth] = useState(0);
  const containerRef = useRef(null);

  const sheetHeight = isHorizontal ? containerWidth * (xSpan / ySpan) : windowHeight * 0.8;
  const sheetWidth = isHorizontal ? containerWidth : (xSpan / ySpan) * windowHeight * 0.8;

  //////////////////
  //Helper Functions
  //////////////////
  const toStage = (x, y) => {
    if (isHorizontal) {
      return [(y - sheetPlotYExtent[0]) * (sheetWidth / ySpan), (x - sheetPlotXExtent[0]) * (sheetHeight / xSpan)];
    }
    return [
      (x - sheetPlotXExtent[0]) * (sheetWidth / xSpan),
      sheetHeight - (y - sheetPlotYExtent[0]) * (sheetHeight / ySpan),
    ];
  };

  const linePoints = (x1, y1, x2, y2) => [...toStage(x1, y1), ...toStage(x2, y2)];

  const sheetDistanceToStageDistance = (d) => {
    return d * (isHorizontal ? sheetWidth / ySpan : sheetWidth / xSpan);
  };

  const getStonePositionAtTime = (stone, current_time) => {
    if (stone.time_history[0] > current_time || stone.time_history[stone.time_history.length - 1] < current_time) {
      return null;
    }

    let index = findInsertionPoint(stone.time_history, current_time);

    const t0 = stone.time_history[index - 1];
    const t1 = stone.time_history[index];
    // A stone's first two samples can share a time, so don't interpolate between equal times
    if (index === 0 || t1 === t0) {
      return [stone.position_history[index][0], stone.position_history[index][1]];
    }
    const fraction = (current_time - t0) / (t1 - t0);
    const [x0, y0] = stone.position_history[index - 1];
    const [x1, y1] = stone.position_history[index];
    return [x0 + (x1 - x0) * fraction, y0 + (y1 - y0) * fraction];
  };

  // The covariance at a time, interpolated linearly between samples like the position
  const getStoneCovarianceAtTime = (stone, current_time) => {
    const covariances = stone.position_covariance_history;
    let index = findInsertionPoint(stone.time_history, current_time);
    const t0 = stone.time_history[index - 1];
    const t1 = stone.time_history[index];
    if (index === 0 || t1 === t0) {
      return covariances[index];
    }
    const fraction = (current_time - t0) / (t1 - t0);
    return covariances[index].map((row, i) =>
      row.map((value, j) => covariances[index - 1][i][j] + (value - covariances[index - 1][i][j]) * fraction),
    );
  };

  // Konva Ellipse props for the 95% region of a sheet position covariance centred on a sheet position
  const covarianceEllipse = ([[xx, xy], [, yy]], x, y) => {
    // Covariance in stage axes: horizontal swaps the axes, vertical flips the y axis
    const scale = sheetDistanceToStageDistance(1) ** 2;
    const [a, b, c] = isHorizontal ? [yy * scale, xy * scale, xx * scale] : [xx * scale, -xy * scale, yy * scale];

    // Closed form eigen decomposition of [[a, b], [b, c]]
    const mean = (a + c) / 2;
    const spread = Math.sqrt(((a - c) / 2) ** 2 + b ** 2);
    const major = mean + spread;
    const minor = Math.max(mean - spread, 0);
    const angle = (Math.atan2(major - a, b) * 180) / Math.PI;

    const [stageX, stageY] = toStage(x, y);
    return {
      x: stageX,
      y: stageY,
      radiusX: Math.sqrt(CHI_SQUARED_95 * major),
      radiusY: Math.sqrt(CHI_SQUARED_95 * minor),
      rotation: b === 0 ? (a >= c ? 0 : 90) : angle,
    };
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
        pathPoints.push(...toStage(stone.position_history[i][0], stone.position_history[i][1]));
      } else {
        break;
      }
    }

    // Add the interpolated current position as the last point
    if (pathPoints.length > 0) {
      pathPoints.push(...toStage(...getStonePositionAtTime(stone, current_time)));
    }
    return pathPoints;
  };

  ///////////////
  //Use Functions
  ///////////////
  const { data } = useQuery({
    queryKey: ["/api/calibration_coordinates"],
    queryFn: () => fetchData(),
  });

  useEffect(() => {
    function handleResize() {
      setWindowHeight(window.innerHeight);
    }

    // Add event listener for window resize
    window.addEventListener("resize", handleResize);

    // Cleanup function to remove the event listener
    return () => window.removeEventListener("resize", handleResize);
  }, []); // Empty dependency array means this effect runs once on mount and once on unmount

  useEffect(() => {
    if (!isHorizontal || containerRef.current === null) {
      return;
    }

    const observer = new ResizeObserver((entries) => setContainerWidth(entries[0].contentRect.width));
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [isHorizontal]);

  const houseCenter = (side) => toStage(data[side + "_pin"][0], data[side + "_pin"][1]);

  return (
    <Box ref={containerRef} width={isHorizontal ? "100%" : undefined}>
      <Stage width={sheetWidth} height={sheetHeight} backgroundColor="white">
        <Layer>
          <Rect x={0} y={0} width={sheetWidth} height={sheetHeight} fill="white" />
        </Layer>

        {data &&
          ["away", "home"].map((side) => (
            <Layer key={side}>
              {[
                [6, "blue"],
                [4, "white"],
                [2, "red"],
                [0.5, "white"],
              ].map(([radius, color]) => (
                <Circle
                  key={radius}
                  x={houseCenter(side)[0]}
                  y={houseCenter(side)[1]}
                  radius={sheetDistanceToStageDistance(radius)}
                  fill={color}
                />
              ))}

              <Line
                points={linePoints(
                  data[side + "_left_hog"][0],
                  data[side + "_left_tee_12"][1],
                  data[side + "_right_hog"][0],
                  data[side + "_right_tee_12"][1],
                )}
                stroke="black"
                strokeWidth={1}
              />

              <Line
                points={linePoints(
                  data[side + "_left_hog"][0],
                  data[side + "_left_backline_corner"][1],
                  data[side + "_right_hog"][0],
                  data[side + "_right_backline_corner"][1],
                )}
                stroke="black"
                strokeWidth={1}
              />

              {/* The hog line is drawn on the side of the line towards the centre of the sheet */}
              <Line
                points={linePoints(
                  data[side + "_left_hog"][0],
                  data[side + "_left_hog"][1] + (side === "away" ? -0.4 : 0.4),
                  data[side + "_right_hog"][0],
                  data[side + "_right_hog"][1] + (side === "away" ? -0.4 : 0.4),
                )}
                stroke="black"
                strokeWidth={sheetDistanceToStageDistance(0.4)}
              />
            </Layer>
          ))}

        {data && (
          <Layer>
            <Line
              points={linePoints(
                data["away_back_center_12"][0],
                data["away_back_center_12"][1],
                data["home_back_center_12"][0],
                data["home_back_center_12"][1],
              )}
              stroke="black"
              strokeWidth={1}
            />

            <Line
              points={linePoints(
                data["away_left_backline_corner"][0],
                data["away_left_backline_corner"][1],
                data["home_left_backline_corner"][0],
                data["home_left_backline_corner"][1],
              )}
              stroke="black"
              strokeWidth={1}
            />

            <Line
              points={linePoints(
                data["away_right_backline_corner"][0],
                data["away_right_backline_corner"][1],
                data["home_right_backline_corner"][0],
                data["home_right_backline_corner"][1],
              )}
              stroke="black"
              strokeWidth={1}
            />
          </Layer>
        )}

        {showUncertainty && (
          <Layer listening={false}>
            {stones &&
              stones.map((stone, index) => {
                if (!stone.position_covariance_history || !getStoneVisibilityAtTime(stone, plotTime)) return null;

                const pathEllipses = [];
                for (let i = 0; i < stone.time_history.length && stone.time_history[i] <= plotTime; i++) {
                  if (i % PATH_ELLIPSE_INTERVAL !== 0) continue;
                  pathEllipses.push(
                    <Ellipse
                      key={`path-ellipse-${index}-${i}`}
                      {...covarianceEllipse(
                        stone.position_covariance_history[i],
                        stone.position_history[i][0],
                        stone.position_history[i][1],
                      )}
                      stroke={ellipseColor(stone.color, 0.7)}
                      strokeWidth={1.5}
                    />,
                  );
                }

                return [
                  ...pathEllipses,
                  <Ellipse
                    key={`ellipse-${index}`}
                    {...covarianceEllipse(
                      getStoneCovarianceAtTime(stone, plotTime),
                      ...getStonePositionAtTime(stone, plotTime),
                    )}
                    stroke={ellipseColor(stone.color, 1)}
                    strokeWidth={2}
                    fill={ellipseColor(stone.color, 0.25)}
                  />,
                ];
              })}
          </Layer>
        )}

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
            stones.map((stone, index) => {
              if (!getStoneVisibilityAtTime(stone, plotTime)) return null;

              const [x, y] = toStage(...getStonePositionAtTime(stone, plotTime));
              return (
                <Circle
                  key={`stone-${index}`}
                  x={x}
                  y={y}
                  radius={sheetDistanceToStageDistance(0.5)}
                  fill={stone.color}
                />
              );
            })}
        </Layer>
      </Stage>
    </Box>
  );
};

export default CurlingSheetPlot;
