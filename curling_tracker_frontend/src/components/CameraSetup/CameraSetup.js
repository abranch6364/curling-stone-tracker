import { useState } from "react";
import { Tabs } from "@chakra-ui/react";

import CameraSelection from "../CameraSelection/CameraSelection";
import CreateCalibration from "../CreateCalibration/CreateCalibration";
import ViewCalibration from "../ViewCalibration/ViewCalibration";
import TestCalibration from "../TestCalibration/TestCalibration";

const CameraSetup = () => {
  const [setupId, setSetupId] = useState("");
  return (
    <Tabs.Root defaultValue="camera_selection" width="100%">
      <Tabs.List>
        <Tabs.Trigger value="camera_selection">Camera Selection</Tabs.Trigger>
        <Tabs.Trigger value="create_calibration">Create Calibration</Tabs.Trigger>
        <Tabs.Trigger value="view_calibration">View Calibration</Tabs.Trigger>
        <Tabs.Trigger value="test_calibration">Test Calibration</Tabs.Trigger>
      </Tabs.List>
      <Tabs.Content value="camera_selection">
        <CameraSelection selectedSetupId={setupId} setSelectedSetupId={setSetupId}></CameraSelection>
      </Tabs.Content>
      <Tabs.Content value="create_calibration">
        <CreateCalibration selectedSetupId={setupId} setSelectedSetupId={setSetupId}></CreateCalibration>
      </Tabs.Content>
      <Tabs.Content value="view_calibration">
        <ViewCalibration selectedSetupId={setupId} setSelectedSetupId={setSetupId}></ViewCalibration>
      </Tabs.Content>

      <Tabs.Content value="test_calibration">
        <TestCalibration selectedSetupId={setupId} setSelectedSetupId={setSetupId}></TestCalibration>
      </Tabs.Content>
    </Tabs.Root>
  );
};

export default CameraSetup;
