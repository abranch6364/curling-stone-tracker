import { useState, useEffect, useRef } from "react";
import { useQueryClient, useQuery, useMutation } from "@tanstack/react-query";
import { Button, Input, HStack, VStack, Text, Heading, Box, RadioGroup, NativeSelect } from "@chakra-ui/react";

import ImageViewer from "../ImageViewer/ImageViewer";
import FetchDropdown from "../FetchDropdown/FetchDropdown";
import { toaster } from "../ui/toaster";

const fetchCameraSetup = async (setupId) => {
  const params = new URLSearchParams({ setup_id: setupId });
  const response = await fetch("/api/camera_setup?" + params, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });
  if (!response.ok) {
    throw new Error("Network response was not ok");
  }

  return response.json();
};

const fetchCalibrationPoints = async (cameraId) => {
  const params = new URLSearchParams({ camera_id: cameraId });
  const response = await fetch("/api/calibration_points?" + params, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });
  if (!response.ok) {
    throw new Error("Network response was not ok");
  }

  return response.json();
};

const saveCalibrationPoints = async ({ cameraId, points, calibrationMethod, referenceCameraId }) => {
  const response = await fetch("/api/calibration_points", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },

    body: JSON.stringify({
      camera_id: cameraId,
      points: points,
      calibration_method: calibrationMethod,
      reference_camera_id: calibrationMethod === "homography" ? referenceCameraId : null,
    }),
  });
  const json = await response.json();
  if (!response.ok) {
    throw new Error(json.error || "Network response was not ok");
  }

  return json;
};

const POINT_SIDES = ["home", "away"];

// "away_left_tee_12" -> "left tee 12"
const pointLabel = (key, side) => key.replace(side + "_", "").replaceAll("_", " ");

const CreateCalibration = ({ selectedSetupId, setSelectedSetupId, calibrationImage }) => {
  const [splitImages, setSplitImages] = useState(null);
  const [pointFilter, setPointFilter] = useState("home");
  const [selectedCameraIndex, setSelectedCameraIndex] = useState(-1);

  const [sheetCoords, setSheetCoords] = useState({});
  const [imageCoords, setImageCoords] = useState({});
  const [selectedKey, setSelectedKey] = useState("");
  const [calibrationMethod, setCalibrationMethod] = useState("full");
  const [referenceCameraId, setReferenceCameraId] = useState("");

  const inputRefs = useRef({});
  const queryClient = useQueryClient();

  //////////////////
  //Helper Functions
  //////////////////
  const setImageCoordsKey = (key, value) => {
    const nextImageCoords = Object.entries(imageCoords).map(([k, v]) => {
      if (k === key) {
        return [k, value];
      } else {
        return [k, v];
      }
    });
    setImageCoords(Object.fromEntries(nextImageCoords));
  };

  const splitImageByCamera = (image) => {
    var imageElement = new Image();
    imageElement.onload = splitImage;
    imageElement.src = URL.createObjectURL(image);

    function splitImage() {
      var newSplitImages = {};
      for (const c of data.cameras) {
        var canvas = document.createElement("canvas");
        var xOrigin = Math.min(c.corner1[0], c.corner2[0]);
        var yOrigin = Math.min(c.corner1[1], c.corner2[1]);
        canvas.width = Math.abs(c.corner1[0] - c.corner2[0]);
        canvas.height = Math.abs(c.corner1[1] - c.corner2[1]);

        var context = canvas.getContext("2d");
        context.drawImage(
          imageElement,
          xOrigin,
          yOrigin,
          canvas.width,
          canvas.height,
          0,
          0,
          canvas.width,
          canvas.height,
        );
        newSplitImages[c.camera_id] = canvas.toDataURL();
      }
      setSplitImages(newSplitImages);
    }
  };

  const isCameraSelected = () => {
    return selectedCameraIndex !== -1;
  };

  const parseImageCoord = (coordStr) => {
    const parts = coordStr.split(",").map((s) => s.trim());
    if (parts.length !== 2 || parts.some((s) => s === "" || !Number.isFinite(Number(s)))) {
      return null;
    }
    return parts.map(Number);
  };

  ///////////////
  //Use Functions
  ///////////////
  const { data, error, isLoading } = useQuery({
    queryKey: ["/api/camera_setup", selectedSetupId],
    queryFn: () => fetchCameraSetup(selectedSetupId),
    initialData: null,
    enabled: selectedSetupId !== "",
    timeToStale: Infinity,
  });

  const selectedCamera = data && isCameraSelected() ? data.cameras[selectedCameraIndex] : undefined;
  const selectedCameraId = selectedCamera?.camera_id;
  const isHomography = calibrationMethod === "homography";

  // A reference camera must use a full calibration
  const referenceOptions = (data?.cameras ?? []).filter(
    (camera) => camera.camera_id !== selectedCameraId && camera.calibration_method === "full",
  );
  const referenceCamera = referenceOptions.find((camera) => camera.camera_id === referenceCameraId);

  const { data: referencePointsData } = useQuery({
    queryKey: ["/api/calibration_points", referenceCameraId],
    queryFn: () => fetchCalibrationPoints(referenceCameraId),
    enabled: isHomography && referenceCameraId !== "",
    staleTime: Infinity,
  });
  const referencePointNames = new Set(
    isHomography ? (referencePointsData?.points ?? []).map((point) => point.name).filter((name) => name !== null) : [],
  );

  const { data: pointsData } = useQuery({
    queryKey: ["/api/calibration_points", selectedCameraId],
    queryFn: () => fetchCalibrationPoints(selectedCameraId),
    enabled: selectedCameraId !== undefined,
    // Refetching would overwrite points that are edited but not yet saved
    staleTime: Infinity,
  });

  const mutation = useMutation({
    mutationFn: saveCalibrationPoints,
    onSuccess: (result) => {
      queryClient.setQueryData(["/api/calibration_points", result.camera_id], {
        camera_id: result.camera_id,
        points: result.points,
      });
      queryClient.invalidateQueries({ queryKey: ["/api/camera_setup"] });

      if (result.calibrated) {
        toaster.create({ type: "success", title: `Saved ${result.points.length} points and calibrated camera` });
      } else {
        toaster.create({
          type: "warning",
          title: `Saved ${result.points.length} points, camera is not calibrated`,
          description: result.calibration_error,
        });
      }
    },
    onError: (error) => {
      toaster.create({ type: "error", title: "Failed to save calibration points", description: error.message });
    },
  });

  useEffect(() => {
    if (calibrationImage !== null && data !== null) {
      splitImageByCamera(calibrationImage);
    }
  }, [data]);

  // Load the saved calibration method of the selected camera
  useEffect(() => {
    setCalibrationMethod(selectedCamera?.calibration_method ?? "full");
    setReferenceCameraId(selectedCamera?.reference_camera_id ?? "");
  }, [selectedCameraId, selectedCamera?.calibration_method, selectedCamera?.reference_camera_id]);

  // Load the saved points of the selected camera into the inputs
  useEffect(() => {
    const nextImageCoords = Object.fromEntries(Object.keys(sheetCoords).map((key) => [key, ""]));
    for (const point of pointsData?.points ?? []) {
      if (point.name in nextImageCoords) {
        nextImageCoords[point.name] = `${point.image_point[0]}, ${point.image_point[1]}`;
      }
    }
    setImageCoords(nextImageCoords);

    // Show the side that has saved points if the current side has none
    const savedSides = POINT_SIDES.filter((side) => (pointsData?.points ?? []).some((p) => p.name?.includes(side)));
    if (savedSides.length > 0) {
      setPointFilter((current) => (savedSides.includes(current) ? current : savedSides[0]));
    }
  }, [pointsData, sheetCoords]);

  useEffect(() => {
    if (calibrationImage !== null && data !== null) {
      splitImageByCamera(calibrationImage);
    }
  }, [calibrationImage]);

  useEffect(() => {
    fetch("/api/calibration_coordinates")
      .then((response) => response.json())
      .then((json) => {
        setSheetCoords(json);
      })
      .catch((error) => console.error(error));
  }, []);

  ///////////
  //Callbacks
  ///////////
  const calibrateCamera = () => {
    if (selectedCameraId === undefined) {
      return;
    }

    const points = [];
    const invalidKeys = [];
    for (const [key, coordStr] of Object.entries(imageCoords)) {
      if (coordStr.trim() === "") {
        continue;
      }
      const imagePoint = parseImageCoord(coordStr);
      if (imagePoint === null) {
        invalidKeys.push(key);
      } else {
        points.push({ name: key, image_point: imagePoint });
      }
    }

    if (invalidKeys.length > 0) {
      toaster.create({
        type: "error",
        title: "Points must be entered as x, y",
        description: invalidKeys.join(", "),
      });
      return;
    }

    // Points without a sheet coordinate name can't be edited here, so send them back unchanged
    const unnamedPoints = (pointsData?.points ?? [])
      .filter((point) => point.name === null)
      .map((point) => ({ name: null, image_point: point.image_point, world_point: point.world_point }));

    mutation.mutate({
      cameraId: selectedCameraId,
      points: [...points, ...unnamedPoints],
      calibrationMethod: calibrationMethod,
      referenceCameraId: referenceCameraId,
    });
  };

  const imagePointsHandleChange = (event, key) => {
    setImageCoordsKey(key, event.target.value);
  };

  const imageViewerClick = (x, y) => {
    if (!(selectedKey in sheetCoords)) {
      return;
    }
    setImageCoordsKey(selectedKey, `${Math.trunc(x)}, ${Math.trunc(y)}`);
    inputRefs.current[selectedKey].focus();
  };

  const onCameraButtonClick = (index) => {
    setSelectedCameraIndex(index);
  };

  const onDropdownChange = (value) => {
    setSelectedCameraIndex(-1);
    setSelectedSetupId(value);
  };

  const visibleKeys = Object.keys(sheetCoords).filter((key) => key.includes(pointFilter));
  const sharedPointCount = Object.entries(imageCoords).filter(
    ([key, value]) => referencePointNames.has(key) && value.trim() !== "",
  ).length;
  const sidePointCount = (side) =>
    Object.entries(imageCoords).filter(([key, value]) => key.includes(side) && value.trim() !== "").length;

  return (
    <HStack alignItems="start">
      <VStack alignItems="start" spacing="10px" marginRight="20px">
        <Heading size="md">Selected Camera Setup</Heading>
        <FetchDropdown
          api_url="/api/camera_setup_headers"
          placeholder="Select Camera Setup"
          jsonToList={(json) => json}
          itemToKey={(item) => item.setup_id}
          itemToString={(item) => item.setup_name}
          value={selectedSetupId}
          setValue={onDropdownChange}
        />

        <Text>Cameras</Text>
        {data &&
          data.cameras.map((camera, index) => (
            <Button
              key={index}
              width="200px"
              justifyContent="flex-start"
              onClick={() => onCameraButtonClick(index)}
              variant={selectedCameraIndex === index ? "solid" : "outline"}
            >
              {camera.camera_name}
            </Button>
          ))}
      </VStack>
      <VStack>
        <ImageViewer
          onImageClick={imageViewerClick}
          file={
            selectedCameraIndex !== -1 && splitImages !== null && data
              ? splitImages[data.cameras[selectedCameraIndex].camera_id]
              : null
          }
        />
      </VStack>

      <VStack align="start" gap="3">
        <HStack gap="4">
          <Button
            onClick={calibrateCamera}
            disabled={selectedCameraId === undefined || mutation.isPending || (isHomography && !referenceCamera)}
          >
            Save Points & Calibrate
          </Button>
          {pointsData && <Text>{pointsData.points.length} points saved</Text>}
          {selectedCamera && (
            <Text color={selectedCamera.calibrated ? "green.fg" : "orange.fg"}>
              {selectedCamera.calibrated ? "Calibrated" : "Not calibrated"}
            </Text>
          )}
        </HStack>

        <RadioGroup.Root
          value={calibrationMethod}
          onValueChange={(details) => setCalibrationMethod(details.value)}
          disabled={selectedCameraId === undefined}
        >
          <HStack gap="6">
            <Heading as="h3" size="md">
              Method
            </Heading>
            {[
              ["full", "Full calibration"],
              ["homography", "Homography"],
            ].map(([value, label]) => (
              <RadioGroup.Item key={value} value={value}>
                <RadioGroup.ItemHiddenInput />
                <RadioGroup.ItemIndicator />
                <RadioGroup.ItemText>{label}</RadioGroup.ItemText>
              </RadioGroup.Item>
            ))}
          </HStack>
        </RadioGroup.Root>

        {isHomography && (
          <HStack gap="3">
            <Text whiteSpace="nowrap">Reference camera</Text>
            <NativeSelect.Root size="sm" width="220px">
              <NativeSelect.Field
                placeholder="Select reference camera"
                value={referenceCameraId}
                onChange={(e) => setReferenceCameraId(e.target.value)}
              >
                {referenceOptions.map((camera) => (
                  <option key={camera.camera_id} value={camera.camera_id}>
                    {camera.camera_name}
                    {camera.calibrated ? "" : " (not calibrated)"}
                  </option>
                ))}
              </NativeSelect.Field>
              <NativeSelect.Indicator />
            </NativeSelect.Root>
            {referenceCamera && (
              <Text fontSize="sm" color={sharedPointCount >= 4 ? "fg.muted" : "orange.fg"}>
                {sharedPointCount} shared points (need 4)
              </Text>
            )}
          </HStack>
        )}

        <RadioGroup.Root value={pointFilter} onValueChange={(details) => setPointFilter(details.value)}>
          <HStack gap="6">
            <Heading as="h3" size="md">
              Side
            </Heading>
            {POINT_SIDES.map((item) => (
              <RadioGroup.Item key={item} value={item}>
                <RadioGroup.ItemHiddenInput />
                <RadioGroup.ItemIndicator />
                <RadioGroup.ItemText>
                  {item} ({sidePointCount(item)})
                </RadioGroup.ItemText>
              </RadioGroup.Item>
            ))}
          </HStack>
        </RadioGroup.Root>

        <Box
          display="grid"
          gridAutoFlow="column"
          gridTemplateRows={`repeat(${Math.ceil(visibleKeys.length / 2)}, auto)`}
          columnGap="4"
          rowGap="1"
        >
          {visibleKeys.map((key) => (
            <HStack
              key={key}
              gap="2"
              paddingX="1"
              borderRadius="sm"
              bg={selectedKey === key ? "bg.emphasized" : undefined}
            >
              {isHomography && (
                <Box
                  width="8px"
                  height="8px"
                  flexShrink="0"
                  borderRadius="full"
                  bg={referencePointNames.has(key) ? "blue.solid" : "transparent"}
                  title={referencePointNames.has(key) ? `Also picked on ${referenceCamera?.camera_name}` : undefined}
                />
              )}
              <Text
                width="150px"
                fontSize="sm"
                whiteSpace="nowrap"
                fontWeight={imageCoords[key] ? "bold" : "normal"}
                color={imageCoords[key] ? undefined : "fg.muted"}
              >
                {pointLabel(key, pointFilter)}
              </Text>
              <Input
                size="xs"
                width="90px"
                type="text"
                placeholder="x, y"
                ref={(el) => (inputRefs.current[key] = el)}
                value={imageCoords[key] ?? ""}
                onChange={(e) => imagePointsHandleChange(e, key)}
                onFocus={() => setSelectedKey(key)}
              />
            </HStack>
          ))}
        </Box>
      </VStack>
    </HStack>
  );
};

export default CreateCalibration;
