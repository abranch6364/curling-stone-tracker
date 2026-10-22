import { Box, Link } from "@chakra-ui/react";
import { LuExternalLink } from "react-icons/lu";

// How often (ms) unfinished runs are checked for progress
const POLL_INTERVAL_MS = 2000;

const FINISHED_STATUSES = ["complete", "failed", "cancelled"];
const STATUS_COLORS = {
  queued: "gray",
  downloading: "blue",
  scanning: "blue",
  tracking: "blue",
  complete: "green",
  failed: "red",
  cancelled: "orange",
};

const isFinished = (status) => FINISHED_STATUSES.includes(status);

// SQLite's CURRENT_TIMESTAMP is UTC without a zone
const formatCreatedAt = (createdAt) => new Date(createdAt.replace(" ", "T") + "Z").toLocaleString();

// A time in a video as h:mm:ss
const formatVideoTime = (seconds) => {
  const total = Math.floor(seconds ?? 0);
  const minutes = String(Math.floor(total / 60) % 60).padStart(2, "0");
  return `${Math.floor(total / 3600)}:${minutes}:${String(total % 60).padStart(2, "0")}`;
};

// When a draw started. A recorded live stream knows when it started, so this is the draw's date and time.
// Other videos only have a date.
// A date like "Tue, Sep 29 2026", built from its parts since the browser's format has a comma before the year
const formatDrawDate = (date) => {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat(undefined, { weekday: "short", year: "numeric", month: "short", day: "numeric" })
      .formatToParts(date)
      .map((part) => [part.type, part.value]),
  );
  return `${parts.weekday}, ${parts.month} ${parts.day} ${parts.year}`;
};

const formatDrawStart = (game) => {
  if (game.video_start_timestamp != null) {
    const start = new Date((game.video_start_timestamp + game.start_seconds) * 1000);
    return `${formatDrawDate(start)}, ${start.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}`;
  }
  if (game.video_date) {
    return formatDrawDate(new Date(`${game.video_date}T00:00`));
  }
  return null;
};

// A shot's back line to hog and hog to hog times, with a dash for a time that couldn't be worked out
const formatSplitTime = (seconds) => (seconds == null ? "—" : `${seconds.toFixed(2)}s`);
const formatSplitTimes = (shot) =>
  `Back Line to Hog ${formatSplitTime(shot.back_line_to_hog_seconds)} · Hog to Hog ${formatSplitTime(
    shot.hog_to_hog_seconds,
  )}`;

// What to call a run's video: its title, or its link if the title isn't known
const videoName = (item) => item.video_title ?? item.url;

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
const youTubeLinkAt = (url, seconds) => {
  const videoId = parseYouTubeId(url);
  return videoId ? `https://www.youtube.com/watch?v=${videoId}&t=${Math.floor(seconds ?? 0)}s` : null;
};

// A short form of a run's id, enough to tell re-runs of a video apart
const shortRunId = (runId) => runId.slice(0, 8);

const fetchJson = async (url, options) => {
  const response = await fetch(url, options);
  const json = await response.json();
  if (!response.ok) {
    throw new Error(json.error || "Network response was not ok");
  }
  return json;
};

// The tracking runs, checked for progress while any of them is unfinished
const trackingRunsQuery = {
  queryKey: ["tracking_runs"],
  queryFn: () => fetchJson("/api/tracking_runs"),
  refetchInterval: (query) => (query.state.data?.some((run) => !isFinished(run.status)) ? POLL_INTERVAL_MS : false),
};

// A link to the video, opening at a time, that doesn't also select the row it's in. Long text is cut short
// rather than the icon after it.
const VideoLink = ({ url, seconds, children }) => {
  const href = youTubeLinkAt(url, seconds) ?? url;
  return (
    <Link
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      title={href}
      display="inline-flex"
      alignItems="center"
      gap="1"
      maxWidth="100%"
      onClick={(event) => event.stopPropagation()}
    >
      <Box as="span" truncate>
        {children}
      </Box>
      <Box as="span" flexShrink="0">
        <LuExternalLink />
      </Box>
    </Link>
  );
};

export {
  POLL_INTERVAL_MS,
  STATUS_COLORS,
  VideoLink,
  fetchJson,
  formatCreatedAt,
  formatDrawStart,
  formatSplitTime,
  formatSplitTimes,
  formatVideoTime,
  isFinished,
  shortRunId,
  trackingRunsQuery,
  videoName,
  youTubeLinkAt,
};
