import { useEffect, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Badge, Button, HStack, Heading, Link, Spinner, Text, VStack } from "@chakra-ui/react";
import { LuExternalLink } from "react-icons/lu";

import SheetPanel from "../SheetPanel/SheetPanel";
// The embedded YouTubePlayer is left out for now, since it isn't working
import { youTubeLinkAt } from "../YouTubePlayer/YouTubePlayer";

import { getStoneMinTime } from "../../utility/CurlingStoneHelper";
import { formatSplitTime, formatVideoTime } from "../../utility/TrackingRunHelper";

// A labelled time, with the value standing out from its label
const SplitTime = ({ label, seconds }) => (
  <Badge size="lg" variant="surface" colorPalette="blue" fontWeight="normal">
    {label}
    <Text as="span" fontWeight="bold" fontSize="md">
      {formatSplitTime(seconds)}
    </Text>
  </Badge>
);

const DIRECTION_LABELS = { to_away: "→ away", to_home: "← home" };

const fetchShot = async (shotId) => {
  const response = await fetch(`/api/shots/${shotId}`);
  const json = await response.json();
  if (!response.ok) {
    throw new Error(json.error || "Network response was not ok");
  }
  return json;
};

// The tracked stones of one shot on the sheet, with a link to the shot in the YouTube video
const ShotViewer = ({ shotId, onShotChange }) => {
  const [sliderTime, setSliderTime] = useState(0);

  const {
    data: shot,
    error,
    isLoading,
  } = useQuery({
    queryKey: ["shot", shotId],
    queryFn: () => fetchShot(shotId),
    // Keeps the video player while the next shot loads
    placeholderData: keepPreviousData,
  });

  const stones = shot?.state.stones ?? [];

  // Start each shot at its first tracked time
  useEffect(() => {
    if (shot) {
      setSliderTime(stones.length > 0 ? getStoneMinTime(stones) : shot.start_seconds);
    }
  }, [shot]);

  if (isLoading) {
    return <Spinner />;
  }
  if (error) {
    return <Text color="fg.error">Failed to load the shot: {error.message}</Text>;
  }

  const youTubeLink = youTubeLinkAt(shot.url, shot.start_seconds);

  return (
    <VStack align="stretch" gap="5" width="100%">
      <HStack justify="space-between" wrap="wrap">
        <VStack align="start" gap="2">
          <Heading as="h3" size="md">
            Draw {shot.game_number} · End {shot.end_number} · Shot {shot.shot_number}
            <Text as="span" fontWeight="normal" color="fg.muted" ms="3">
              {shot.color} {DIRECTION_LABELS[shot.direction]} · {formatVideoTime(shot.start_seconds)}
            </Text>
          </Heading>
          <HStack gap="2" wrap="wrap">
            <SplitTime label="Back Line to Hog" seconds={shot.back_line_to_hog_seconds} />
            <SplitTime label="Hog to Hog" seconds={shot.hog_to_hog_seconds} />
          </HStack>
        </VStack>
        <HStack>
          {youTubeLink && (
            <Link href={youTubeLink} target="_blank" rel="noopener noreferrer" fontSize="sm" me="2">
              Watch on YouTube <LuExternalLink />
            </Link>
          )}
          <Button
            size="sm"
            variant="outline"
            disabled={!shot.previous_shot_id}
            onClick={() => onShotChange(shot.previous_shot_id)}
          >
            Previous shot
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={!shot.next_shot_id}
            onClick={() => onShotChange(shot.next_shot_id)}
          >
            Next shot
          </Button>
        </HStack>
      </HStack>

      {stones.length === 0 && <Text color="fg.muted">No stones were tracked in this shot.</Text>}
      <SheetPanel stones={stones} sliderTime={sliderTime} onSliderTimeChange={setSliderTime} />
    </VStack>
  );
};

export default ShotViewer;
