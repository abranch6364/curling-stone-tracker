import { useState } from "react";
import { HStack, VStack, Heading, SegmentGroup, Switch } from "@chakra-ui/react";

import CurlingSheetPlot from "../CurlingSheetPlot/CurlingSheetPlot";
import AnimationSlider from "../AnimationSlider/AnimationSlider";

import { getStoneMinTime, getStoneMaxTime } from "../../utility/CurlingStoneHelper";

const SHOW_UNCERTAINTY_STORAGE_KEY = "videoDetect.showUncertainty";

// The part of the sheet shown for each zoom level, as [min, max] y in feet
const SHEET_ZOOM_EXTENTS = {
  full: [-65, 65],
  home: [-65, -20],
  away: [20, 65],
};

const loadShowUncertainty = () => {
  try {
    return localStorage.getItem(SHOW_UNCERTAINTY_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
};

// The sheet with the tracked stones at a time, and a slider to pick the time
const SheetPanel = ({ stones, sliderTime, onSliderTimeChange, showPlayButton = true }) => {
  const [sheetZoom, setSheetZoom] = useState("full");
  const [showUncertainty, setShowUncertainty] = useState(loadShowUncertainty);

  const onShowUncertaintyChange = (checked) => {
    setShowUncertainty(checked);
    try {
      localStorage.setItem(SHOW_UNCERTAINTY_STORAGE_KEY, String(checked));
    } catch {
      // Remembering the setting is only a convenience
    }
  };

  return (
    <VStack align="stretch" gap="2">
      <HStack justify="space-between">
        <Heading as="h3" size="md">
          Sheet
        </Heading>
        <HStack gap="6">
          <Switch.Root
            size="sm"
            checked={showUncertainty}
            onCheckedChange={(details) => onShowUncertaintyChange(details.checked)}
          >
            <Switch.HiddenInput />
            <Switch.Control />
            <Switch.Label>Uncertainty (95%)</Switch.Label>
          </Switch.Root>
          <SegmentGroup.Root size="sm" value={sheetZoom} onValueChange={(details) => setSheetZoom(details.value)}>
            <SegmentGroup.Indicator />
            <SegmentGroup.Items
              items={[
                { value: "full", label: "Full" },
                { value: "home", label: "Home" },
                { value: "away", label: "Away" },
              ]}
            />
          </SegmentGroup.Root>
        </HStack>
      </HStack>
      <CurlingSheetPlot
        orientation="horizontal"
        plotTime={sliderTime}
        stones={stones}
        sheetPlotYExtent={SHEET_ZOOM_EXTENTS[sheetZoom]}
        showUncertainty={showUncertainty}
      />
      <AnimationSlider
        sliderTime={sliderTime}
        onSliderTimeChange={onSliderTimeChange}
        sliderMin={getStoneMinTime(stones)}
        sliderMax={getStoneMaxTime(stones)}
        showPlayButton={showPlayButton}
      />
    </VStack>
  );
};

export default SheetPanel;
