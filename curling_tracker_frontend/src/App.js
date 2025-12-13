import logo from './logo.svg';
import './App.css';
import Calibration from './components/Calibration/Calibration';
import { Provider } from "./components/ui/provider";
import { Tabs, Text } from "@chakra-ui/react"

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const App = () => {

  const queryClient = new QueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      <Provider>
        <Tabs.Root defaultValue="calibration">
            <Tabs.List>
              <Tabs.Trigger value="calibration">Calibration</Tabs.Trigger>
              <Tabs.Trigger value="upload-image">Upload Image</Tabs.Trigger>
            </Tabs.List>
            <Tabs.Content value="calibration">
              <Calibration/>
            </Tabs.Content>
            <Tabs.Content value="upload-image">
              <Text>Upload Image Coming Soon!</Text>
            </Tabs.Content>
        </Tabs.Root>
      </Provider>
    </QueryClientProvider>
  );
};

export default App;
