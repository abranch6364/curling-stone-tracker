import { Box, Link } from "@chakra-ui/react";
import { LuExternalLink } from "react-icons/lu";

import { youTubeLinkAt } from "../components/YouTubePlayer/YouTubePlayer";

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

// When a draw started. A recorded live stream knows when it started, so this is the draw's date and time.
// Other videos only have a date.
// A date like "Tue, Sep 29 2026", built from its parts since the browser's format has a comma before the year
const formatDrawDate = (date) => {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat(undefined, { weekday: "short", year: "numeric", month: "short", day: "numeric" })
      .formatToParts(date)
      .map((part) => [part.type, part.value])
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

// What to call a run's video: its title, or its link if the title isn't known
const videoName = (item) => item.video_title ?? item.url;

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
  isFinished,
  shortRunId,
  trackingRunsQuery,
  videoName,
};
