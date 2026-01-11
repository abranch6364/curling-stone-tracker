/**
 * Finds the index where the target should be inserted to maintain sorted order.
 * Assumes the input array `nums` is sorted in ascending order.
 * @param {number[]} nums - The sorted array.
 * @param {number} target - The value to insert.
 * @returns {number} The insertion index.
 */
function findInsertionPoint(nums, target) {
  let left = 0;
  let right = nums.length - 1; // Use a closed interval [left, right]

  while (left <= right) {
    // Calculate the middle index
    const mid = Math.floor((left + right) / 2);

    if (nums[mid] < target) {
      // Target is in the right half, update the left boundary
      left = mid + 1;
    } else if (nums[mid] > target) {
      // Target is in the left half, update the right boundary
      right = mid - 1;
    } else {
      // If the target is found, return that index (for the leftmost occurrence)
      return mid;
    }
  }

  // If the loop finishes without finding the target, 'left' points to
  // the correct insertion point (the index of the first element greater than target).
  return left;
}

function getStoneMinTime(stones) {
  if (!stones || stones.length === 0) {
    return 0;
  }

  let minTime = Infinity;
  for (const stone of stones) {
    for (const t of stone.time_history) {
      if (t < minTime) {
        minTime = t;
      }
    }
  }
  return minTime;
}

function getStoneMaxTime(stones) {
  if (!stones || stones.length === 0) {
    return 0;
  }

  let maxTime = -Infinity;
  for (const stone of stones) {
    for (const t of stone.time_history) {
      if (t > maxTime) {
        maxTime = t;
      }
    }
  }
  return maxTime;
}

const toIntPercent = (x, size) => {
  return 100 * (x / size);
};

export { findInsertionPoint, getStoneMinTime, getStoneMaxTime, toIntPercent };
