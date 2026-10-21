import { useEffect, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Button, HStack, Heading, Link, Spinner, Text, VStack } from "@chakra-ui/react";
import { LuExternalLink } from "react-icons/lu";

import SheetPanel from "../SheetPanel/SheetPanel";
import YouTubePlayer, { youTubeLinkAt } from "../YouTubePlayer/YouTubePlayer";

import { formatVideoTime, getStoneMinTime } from "../../utility/CurlingStoneHelper";

const DIRECTION_LABELS = { to_away: "→ away", to_home: "← home" };

const fetchShot = async (shotId) => {
  const response = await fetch(`/api/shots/${shotId}`);
  const json = await response.json();
  if (!response.ok) {
    throw new Error(json.error || "Network response was not ok");
  }
  return json;
};

// The tracked stones of one shot on the sheet, next to the shot in the YouTube video
const ShotViewer = ({ shotId, onShotChange }) => {
  const [sliderTime, setSliderTime] = useState(0);

  const { data: shot, error, isLoading } = useQuery({
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
        <Heading as="h3" size="md">
          Game {shot.game_number} · End {shot.end_number} · Shot {shot.shot_number}
          <Text as="span" fontWeight="normal" color="fg.muted" ms="3">
            {shot.color} {DIRECTION_LABELS[shot.direction]} · {formatVideoTime(shot.start_seconds)}
          </Text>
        </Heading>
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
      <SheetPanel stones={stones} sliderTime={sliderTime} onSliderTimeChange={setSliderTime} showPlayButton={false} />

      <YouTubePlayer
        url={shot.url}
        startSeconds={shot.start_seconds}
        time={sliderTime}
        onTimeChange={setSliderTime}
      />
    </VStack>
  );
};

export default ShotViewer;
