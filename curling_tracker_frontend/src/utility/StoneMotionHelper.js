// A stone's motion over a shot, as series for charts: position, velocity or acceleration, as its x part (across
// the sheet), y part (down the sheet) or combined. Both parts are measured from the thrower's point of view,
// whichever way the shot went: y is positive forwards, down the sheet, and x is positive to the thrower's right.

// Standard deviations either side of a value for its 95% band, the same as the sheet's uncertainty ellipses
const BAND_STDS = 1.96;
// Below this speed (ft/s) a stone is treated as stopped, so it has no direction of travel to accelerate along
const STOPPED_SPEED = 0.1;

const HISTORIES = {
  position: "position_history",
  velocity: "velocity_history",
  acceleration: "acceleration_history",
};

const LABELS = {
  position: { x: "Position Across", y: "Distance Down Sheet", combined: "Distance From Start" },
  velocity: { x: "Velocity Across", y: "Velocity Down Sheet", combined: "Speed" },
  acceleration: { x: "Acceleration Across", y: "Acceleration Down Sheet", combined: "Acceleration Along Path" },
};

const UNITS = { position: "ft", velocity: "ft/s", acceleration: "ft/s²" };

const motionLabel = (quantity, component) => `${LABELS[quantity][component]} (${UNITS[quantity]})`;

// The standard deviation of a position's distance from the start, from the position's covariance. It's the
// covariance along the direction from the start (ignoring the start's own error). Right at the start there's no
// direction, so the average of the two axes is used.
const distanceStd = (covariance, dx, dy, distance) => {
  if (distance < 1e-6) {
    return Math.sqrt((covariance[0][0] + covariance[1][1]) / 2);
  }
  const ux = dx / distance;
  const uy = dy / distance;
  const variance = ux * ux * covariance[0][0] + 2 * ux * uy * covariance[0][1] + uy * uy * covariance[1][1];
  return Math.sqrt(Math.max(variance, 0));
};

/**
 * A stone's motion as one point per tracked time.
 * @param {object} stone - The stone, with time_history, position/velocity/acceleration_history and
 *   position_covariance_history
 * @param {string} quantity - "position", "velocity" or "acceleration"
 * @param {string} component - "x", "y" or "combined". Combined is the distance from the start for position, the
 *   speed for velocity, and for acceleration the part along the stone's direction of travel, so it's negative
 *   while the stone slows down.
 * @param {number} startTime - The time that's 0 on the chart (s)
 * @param {string} direction - The way the shot was thrown, "to_away" or "to_home". The y parts are positive
 *   forwards in this direction, and the x parts positive to the thrower's right.
 * @returns {{t: number, value: number, band: ?number[]}[]} The time from startTime, the value, and for position
 *   its 95% band as [low, high] (null for velocity and acceleration, whose uncertainty isn't stored)
 */
const motionSeries = (stone, quantity, component, startTime, direction) => {
  const history = stone[HISTORIES[quantity]];
  const covariances = quantity === "position" ? stone.position_covariance_history : null;
  const [startX, startY] = stone.position_history[0];
  // Sheet coordinates are as seen by a thrower facing the away end: y forwards, x to their right. A thrower facing
  // the home end is turned around, so both are flipped.
  const flip = direction === "to_home" ? -1 : 1;

  const points = [];
  for (let i = 0; i < stone.time_history.length; i++) {
    const [x, y] = history[i];
    let value;
    let std = null;
    if (component === "x") {
      value = flip * x;
      std = covariances ? Math.sqrt(covariances[i][0][0]) : null;
    } else if (component === "y") {
      value = flip * y;
      std = covariances ? Math.sqrt(covariances[i][1][1]) : null;
    } else if (quantity === "position") {
      value = Math.hypot(x - startX, y - startY);
      std = covariances ? distanceStd(covariances[i], x - startX, y - startY, value) : null;
    } else if (quantity === "velocity") {
      value = Math.hypot(x, y);
    } else {
      // The acceleration along the direction of travel: positive speeding up, negative slowing down
      const [vx, vy] = stone.velocity_history[i];
      const speed = Math.hypot(vx, vy);
      value = speed < STOPPED_SPEED ? 0 : (x * vx + y * vy) / speed;
    }

    points.push({
      t: stone.time_history[i] - startTime,
      value,
      band: std === null ? null : [value - BAND_STDS * std, value + BAND_STDS * std],
    });
  }
  return points;
};

export { motionLabel, motionSeries };
