import { useState } from "react";
import { Box, HStack, VStack, Heading, SegmentGroup, Switch } from "@chakra-ui/react";

import CurlingSheetPlot from "../CurlingSheetPlot/CurlingSheetPlot";
import AnimationSlider from "../AnimationSlider/AnimationSlider";

import { getStoneMinTime, getStoneMaxTime } from "../../utility/CurlingStoneHelper";
import useIsPhone from "../../utility/useIsPhone";

const SHOW_UNCERTAINTY_STORAGE_KEY = "videoDetect.showUncertainty";

// The part of the sheet shown for each zoom level, as [min, max] y in feet
const SHEET_ZOOM_EXTENTS = {
  full: [-65, 65],
  home: [-65, -20],
  away: [20, 65],
};

// On a phone the sheet is upright and seen from the delivering end, so the house the shot is thrown to is at the
// top. These extents are along the sheet from there: the house is from just short of the far hog line to just past
// the back line, which fills most of a phone screen.
const PHONE_ZOOM_EXTENTS = {
  house: [34, 64],
  full: [-65, 65],
};

const loadShowUncertainty = () => {
  try {
    return localStorage.getItem(SHOW_UNCERTAINTY_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
};

// The sheet with the tracked stones at a time, and a slider to pick the time. direction is the way the shot was
// thrown (to_away or to_home), which a phone uses to turn the sheet so the shot goes up the screen.
const SheetPanel = ({ stones, sliderTime, onSliderTimeChange, showPlayButton = true, direction = "to_away" }) => {
  const isPhone = useIsPhone();
  const [sheetZoom, setSheetZoom] = useState("full");
  const [phoneZoom, setPhoneZoom] = useState("house");
  const [showUncertainty, setShowUncertainty] = useState(loadShowUncertainty);

  const onShowUncertaintyChange = (checked) => {
    setShowUncertainty(checked);
    try {
      localStorage.setItem(SHOW_UNCERTAINTY_STORAGE_KEY, String(checked));
    } catch {
      // Remembering the setting is only a convenience
    }
  };

  const zoomItems = isPhone
    ? [
        { value: "house", label: "House" },
        { value: "full", label: "Full" },
      ]
    : [
        { value: "full", label: "Full" },
        { value: "home", label: "Home" },
        { value: "away", label: "Away" },
      ];

  return (
    <VStack align="stretch" gap="2">
      <HStack justify="space-between" wrap="wrap" gap="3">
        <Heading as="h3" size="md">
          Sheet
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
          <SegmentGroup.Root
            size="sm"
            value={isPhone ? phoneZoom : sheetZoom}
            onValueChange={(details) => (isPhone ? setPhoneZoom : setSheetZoom)(details.value)}
          >
            <SegmentGroup.Indicator />
            <SegmentGroup.Items items={zoomItems} />
          </SegmentGroup.Root>
        </HStack>
      </HStack>
      {isPhone ? (
        <CurlingSheetPlot
          orientation="vertical"
          fitWidth
          flipped={direction === "to_home"}
          plotTime={sliderTime}
          stones={stones}
          sheetPlotYExtent={PHONE_ZOOM_EXTENTS[phoneZoom]}
          showUncertainty={showUncertainty}
        />
      ) : (
        <CurlingSheetPlot
          orientation="horizontal"
          plotTime={sliderTime}
          stones={stones}
          sheetPlotYExtent={SHEET_ZOOM_EXTENTS[sheetZoom]}
          showUncertainty={showUncertainty}
        />
      )}
      {/* On a phone the sheet can be taller than the screen, so the slider stays at the bottom of it */}
      <Box position={isPhone ? "sticky" : undefined} bottom="0" bg="bg" py={isPhone ? "2" : undefined} zIndex="1">
        <AnimationSlider
          sliderTime={sliderTime}
          onSliderTimeChange={onSliderTimeChange}
          sliderMin={getStoneMinTime(stones)}
          sliderMax={getStoneMaxTime(stones)}
          showPlayButton={showPlayButton}
        />
      </Box>
    </VStack>
  );
};

export default SheetPanel;
