import { useMemo, useRef, useState } from "react";
import { Chart, useChart } from "@chakra-ui/charts";
import { Grid, HStack, Heading, SegmentGroup, Switch, Text, VStack } from "@chakra-ui/react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  useXAxisInverseScale,
} from "recharts";

import { motionLabel, motionSeries } from "../../utility/StoneMotionHelper";

const SHOW_UNCERTAINTY_STORAGE_KEY = "shotViewer.showMotionUncertainty";
const QUANTITIES = ["position", "velocity", "acceleration"];
const COMPONENT_ITEMS = [
  { value: "y", label: "Down sheet" },
  { value: "x", label: "Across" },
  { value: "combined", label: "Total" },
];
const CHART_HEIGHT = { base: "150px", lg: "200px" };
// The charts are stacked on narrow screens, and side by side on a desktop so they're all seen at once
const CHART_COLUMNS = { base: "minmax(0, 1fr)", lg: "repeat(3, minmax(0, 1fr))" };

const loadShowUncertainty = () => {
  try {
    return localStorage.getItem(SHOW_UNCERTAINTY_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
};

// Keeps the chart's x axis inverse scale (from a position in the chart to a time) in a ref, for clicks. Recharts'
// own click data only knows the point under a hovering mouse, so it misses taps on a phone.
// A y axis label, muted like the other labels except 0, which is bold so the zero line is easy to find
const YAxisTick = ({ x, y, payload, mutedColor, zeroColor }) => (
  <text
    x={x}
    y={y}
    dy={4}
    textAnchor="end"
    style={{ fill: payload.value === 0 ? zeroColor : mutedColor }}
    fontWeight={payload.value === 0 ? "bold" : "normal"}
  >
    {payload.value.toFixed(1)}
  </text>
);

const XAxisInverseScale = ({ scaleRef }) => {
  scaleRef.current = useXAxisInverseScale();
  return null;
};

// One quantity of the stone's motion over the shot, with a line at the current time. Clicking or tapping it
// moves the current time there.
const MotionChart = ({ points, label, color, maxTime, currentTime, showBand, onTimeClick }) => {
  const chart = useChart({ data: points, series: [{ name: "value", color: `${color}.solid`, label }] });
  const inverseScaleRef = useRef(null);

  const onClick = (event) => {
    const inverseScale = inverseScaleRef.current;
    if (!inverseScale) {
      return;
    }
    const time = Number(inverseScale(event.clientX - event.currentTarget.getBoundingClientRect().left));
    if (Number.isFinite(time)) {
      onTimeClick(Math.min(Math.max(time, 0), maxTime));
    }
  };

  return (
    <VStack align="stretch" gap="1">
      <Text fontSize="sm" fontWeight="medium">
        {label}
      </Text>
      <Chart.Root chart={chart} aspectRatio="auto" height={CHART_HEIGHT} cursor="pointer" onClick={onClick}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chart.data} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
            <XAxisInverseScale scaleRef={inverseScaleRef} />
            <CartesianGrid stroke={chart.color("border")} vertical={false} />
            <XAxis
              dataKey="t"
              type="number"
              domain={[0, maxTime]}
              allowDataOverflow
              tickFormatter={(t) => `${t.toFixed(0)}s`}
              stroke={chart.color("border")}
            />
            <YAxis width={44} tick={<YAxisTick mutedColor={chart.color("fg.muted")} zeroColor={chart.color("fg")} />} stroke={chart.color("border")} />
            {/* Only drawn when 0 is in the chart's range */}
            <ReferenceLine y={0} stroke={chart.color("fg.muted")} strokeWidth={1.5} />
            <Tooltip
              animationDuration={0}
              content={
                <Chart.Tooltip
                  hideIndicator
                  labelFormatter={(_, payload) => `${payload?.[0]?.payload.t.toFixed(2)} s`}
                  formatter={(value) =>
                    // The uncertainty band's value is its [low, high]
                    Array.isArray(value)
                      ? [`${value[0].toFixed(2)} – ${value[1].toFixed(2)}`, "95% range"]
                      : [value.toFixed(2), label]
                  }
                />
              }
            />
            {showBand && (
              <Area
                dataKey="band"
                stroke="none"
                fill={chart.color(`${color}.solid`)}
                fillOpacity={0.2}
                isAnimationActive={false}
                activeDot={false}
              />
            )}
            <Line
              dataKey="value"
              stroke={chart.color(`${color}.solid`)}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
            <ReferenceLine x={currentTime} stroke={chart.color("fg.muted")} strokeDasharray="4 3" />
          </ComposedChart>
        </ResponsiveContainer>
      </Chart.Root>
    </VStack>
  );
};

// Charts of a stone's position, velocity and acceleration over a shot, sharing the sheet's current time.
// startSeconds is the time shown as 0, and direction (to_away or to_home) is the way the shot was thrown.
const MotionCharts = ({ stone, direction, startSeconds, sliderTime, onSliderTimeChange }) => {
  const [component, setComponent] = useState("combined");
  const [showUncertainty, setShowUncertainty] = useState(loadShowUncertainty);

  const onShowUncertaintyChange = (checked) => {
    setShowUncertainty(checked);
    try {
      localStorage.setItem(SHOW_UNCERTAINTY_STORAGE_KEY, String(checked));
    } catch {
      // Remembering the setting is only a convenience
    }
  };

  // Only built again when the stone or the component changes, not as the time plays
  const series = useMemo(() => {
    const byQuantity = {};
    for (const quantity of QUANTITIES) {
      byQuantity[quantity] = motionSeries(stone, quantity, component, startSeconds, direction);
    }
    return byQuantity;
  }, [stone, component, startSeconds, direction]);

  const maxTime = stone.time_history[stone.time_history.length - 1] - startSeconds;

  return (
    <VStack align="stretch" gap="2">
      <HStack justify="space-between" wrap="wrap" gap="3">
        <Heading as="h3" size="md">
          Motion
        </Heading>
        <HStack gap={{ base: "4", md: "6" }} wrap="wrap">
          <Switch.Root
            size="sm"
            checked={showUncertainty}
            onCheckedChange={(details) => onShowUncertaintyChange(details.checked)}
          >
            <Switch.HiddenInput />
            <Switch.Control />
            <Switch.Label>Uncertainty (95%)</Switch.Label>
          </Switch.Root>
          <SegmentGroup.Root size="sm" value={component} onValueChange={(details) => setComponent(details.value)}>
            <SegmentGroup.Indicator />
            <SegmentGroup.Items items={COMPONENT_ITEMS} />
          </SegmentGroup.Root>
        </HStack>
      </HStack>
      {showUncertainty && (
        <Text fontSize="xs" color="fg.muted">
          Uncertainty is only known for position.
        </Text>
      )}
      <Grid templateColumns={CHART_COLUMNS} columnGap="6" rowGap="3">
        {QUANTITIES.map((quantity) => (
          <MotionChart
            key={quantity}
            points={series[quantity]}
            label={motionLabel(quantity, component)}
            color={stone.color}
            maxTime={maxTime}
            currentTime={sliderTime - startSeconds}
            showBand={showUncertainty && quantity === "position"}
            onTimeClick={(time) => onSliderTimeChange(startSeconds + time)}
          />
        ))}
      </Grid>
    </VStack>
  );
};

export default MotionCharts;
