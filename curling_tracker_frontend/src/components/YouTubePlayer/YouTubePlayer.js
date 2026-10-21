import { useEffect, useRef, useState } from "react";
import { AspectRatio, Box, Text } from "@chakra-ui/react";

// How often (ms) the playing video's time is read
const TIME_POLL_INTERVAL_MS = 100;
// A requested time further than this (s) from the video's time is a seek, not the video playing
const SEEK_THRESHOLD_SECONDS = 0.5;

const ERROR_MESSAGES = {
  2: "The video link is not valid.",
  5: "The video can't be played in this browser.",
  100: "The video was not found, or it is private.",
  101: "The owner of this video doesn't allow it to be embedded.",
  150: "The owner of this video doesn't allow it to be embedded.",
};

let youTubeApiPromise = null;

// Load the YouTube IFrame Player API once for the whole page
const loadYouTubeApi = () => {
  if (window.YT && window.YT.Player) {
    return Promise.resolve(window.YT);
  }
  if (!youTubeApiPromise) {
    youTubeApiPromise = new Promise((resolve) => {
      const previousReady = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => {
        previousReady?.();
        resolve(window.YT);
      };
      const script = document.createElement("script");
      script.src = "https://www.youtube.com/iframe_api";
      document.body.appendChild(script);
    });
  }
  return youTubeApiPromise;
};

// The id of a YouTube video from its watch, share, live, shorts or embed link
const parseYouTubeId = (url) => {
  try {
    const parsed = new URL(url);
    if (parsed.hostname.endsWith("youtu.be")) {
      return parsed.pathname.slice(1).split("/")[0] || null;
    }
    if (parsed.searchParams.get("v")) {
      return parsed.searchParams.get("v");
    }
    const match = parsed.pathname.match(/^\/(?:live|shorts|embed)\/([^/?]+)/);
    return match ? match[1] : null;
  } catch {
    return null;
  }
};

// A link to a YouTube video that starts at a time, or null if the link isn't a YouTube video
export const youTubeLinkAt = (url, seconds) => {
  const videoId = parseYouTubeId(url);
  return videoId ? `https://www.youtube.com/watch?v=${videoId}&t=${Math.floor(seconds ?? 0)}s` : null;
};

// An embedded YouTube video kept in step with a time: the playing video reports its time through
// onTimeChange, and changing time while the video isn't there seeks it
const YouTubePlayer = ({ url, startSeconds, time, onTimeChange }) => {
  const containerRef = useRef(null);
  const playerRef = useRef(null);
  const reportedTimeRef = useRef(null);
  const onTimeChangeRef = useRef(onTimeChange);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState(null);

  const videoId = parseYouTubeId(url);
  onTimeChangeRef.current = onTimeChange;

  ///////////////
  //Use Functions
  ///////////////

  // Create the player for the video
  useEffect(() => {
    if (!videoId) {
      return;
    }
    const container = containerRef.current;
    let cancelled = false;
    setIsReady(false);
    setError(null);

    loadYouTubeApi().then((YT) => {
      if (cancelled) {
        return;
      }
      // The player replaces this element with its iframe, so React doesn't manage it
      const element = document.createElement("div");
      container.appendChild(element);
      playerRef.current = new YT.Player(element, {
        width: "100%",
        height: "100%",
        videoId: videoId,
        playerVars: { start: Math.floor(startSeconds ?? 0), rel: 0 },
        events: {
          onReady: () => setIsReady(true),
          onError: (event) => setError(ERROR_MESSAGES[event.data] ?? `The video failed to play (error ${event.data}).`),
        },
      });
    });

    return () => {
      cancelled = true;
      playerRef.current?.destroy();
      playerRef.current = null;
      container.innerHTML = "";
    };
    // The start only matters when the player is created, later shots seek through time
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [videoId]);

  // Report the time while the video plays
  useEffect(() => {
    if (!isReady) {
      return;
    }
    const interval = setInterval(() => {
      const player = playerRef.current;
      if (player && player.getPlayerState() === window.YT.PlayerState.PLAYING) {
        const currentTime = player.getCurrentTime();
        reportedTimeRef.current = currentTime;
        onTimeChangeRef.current?.(currentTime);
      }
    }, TIME_POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [isReady]);

  // Seek when the time is changed from outside, e.g. by dragging the sheet's slider
  useEffect(() => {
    if (!isReady || time === undefined) {
      return;
    }
    if (reportedTimeRef.current === null || Math.abs(time - reportedTimeRef.current) > SEEK_THRESHOLD_SECONDS) {
      seekTo(time);
    }
  }, [time, isReady]);

  //////////////////
  //Helper Functions
  //////////////////

  const seekTo = (seconds) => {
    const player = playerRef.current;
    if (!player) {
      return;
    }
    const wasPlaying = player.getPlayerState() === window.YT.PlayerState.PLAYING;
    player.seekTo(seconds, true);
    // Seeking starts a video that hasn't been played yet, but scrubbing shouldn't
    if (!wasPlaying) {
      player.pauseVideo();
    }
    reportedTimeRef.current = seconds;
  };

  if (!videoId) {
    return <Text color="fg.error">The video link isn't a YouTube video: {url}</Text>;
  }

  return (
    <Box width="100%" maxWidth="960px">
      {error && <Text color="fg.error">{error}</Text>}
      <AspectRatio ratio={16 / 9} width="100%">
        <Box ref={containerRef} bg="black" />
      </AspectRatio>
    </Box>
  );
};

export default YouTubePlayer;
