import { Link } from "@chakra-ui/react";
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
const formatDrawStart = (game) => {
  if (game.video_start_timestamp != null) {
    return new Date((game.video_start_timestamp + game.start_seconds) * 1000).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  }
  if (game.video_date) {
    return new Date(`${game.video_date}T00:00`).toLocaleDateString(undefined, { dateStyle: "medium" });
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

// A link to the video, opening at a time, that doesn't also select the row it's in
const VideoLink = ({ url, seconds, children }) => {
  const href = youTubeLinkAt(url, seconds) ?? url;
  return (
    <Link
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      title={href}
      onClick={(event) => event.stopPropagation()}
    >
      {children} <LuExternalLink />
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
