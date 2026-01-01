import { Provider } from "./components/ui/provider";
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import TopLevel from './components/TopLevel/TopLevel';

const App = () => {
  const queryClient = new QueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      <Provider>
        <TopLevel/>
      </Provider>
    </QueryClientProvider>
  );
};

export default App;
