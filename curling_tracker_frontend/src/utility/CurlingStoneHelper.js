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

/**
 * Converts a Base64 data URL string into a File object.
 * @param {string} base64String The Base64 string (including data URL prefix, e.g., 'data:image/png;base64,...').
 * @param {string} fileName The name for the resulting file (e.g., 'my-image.png').
 * @returns {File} The File object.
 */
function base64ToFile(base64String, fileName) {
  // Split the string to separate the MIME type and the actual Base64 data
  const arr = base64String.split(",");
  const mime = arr[0].match(/:(.*?);/)[1];
  const bstr = atob(arr[1]);
  const uint8Array = new Uint8Array(bstr.length);

  for (let n = 0; n < bstr.length; n++) {
    uint8Array[n] = bstr.charCodeAt(n);
  }

  // Create a Blob object
  const blob = new Blob([uint8Array], { type: mime });

  // Create and return the File object
  return new File([blob], fileName, { type: mime, lastModified: new Date().getTime() });
}

export { base64ToFile, findInsertionPoint, getStoneMinTime, getStoneMaxTime, toIntPercent };
