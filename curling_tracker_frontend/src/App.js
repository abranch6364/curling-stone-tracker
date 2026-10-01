import { Provider } from "./components/ui/provider";
import { Toaster } from "./components/ui/toaster";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import TopLevel from "./components/TopLevel/TopLevel";

const App = () => {
  const queryClient = new QueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      <Provider>
        <TopLevel />
        <Toaster />
      </Provider>
    </QueryClientProvider>
  );
};

export default App;
