import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { MantineProvider } from '@mantine/core'
import { queryClient } from './api/queryClient'
import { theme } from './theme'
import App from './App'
import '@mantine/core/styles.css'
import './style.css'

createRoot(document.getElementById('root')).render(
  <QueryClientProvider client={queryClient}>
    <MantineProvider theme={theme} forceColorScheme="light">
      <App />
    </MantineProvider>
  </QueryClientProvider>,
)
