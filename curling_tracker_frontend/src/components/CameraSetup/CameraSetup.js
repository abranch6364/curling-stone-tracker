
import { Text, Tabs } from "@chakra-ui/react"
import CameraSelection from "../CameraSelection/CameraSelection";
import Calibration from "../Calibration/Calibration";
const CameraSetup = () => {

  return (
    <Tabs.Root defaultValue="camera_selection" width="100%">
        <Tabs.List>
          <Tabs.Trigger value="camera_selection">Camera Selection</Tabs.Trigger>
          <Tabs.Trigger value="calibration">Calibration</Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="camera_selection">
          <CameraSelection></CameraSelection>
        </Tabs.Content>
        <Tabs.Content value="calibration">
          <Calibration></Calibration>
        </Tabs.Content>
    </Tabs.Root>
  );
};

export default CameraSetup;