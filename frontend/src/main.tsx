import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { App } from './App.tsx'
import './index.css'
import { CostPage } from './pages/Cost.tsx'
import { Dashboard } from './pages/Dashboard.tsx'
import { History } from './pages/History.tsx'
import { JobDetail } from './pages/JobDetail.tsx'
import { NewJob } from './pages/NewJob.tsx'
import { SettingsPage } from './pages/Settings.tsx'

const qc = new QueryClient({
  defaultOptions: { queries: { staleTime: 1000, retry: 1 } },
})

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'history', element: <History /> },
      { path: 'jobs/new', element: <NewJob /> },
      { path: 'jobs/:id', element: <JobDetail /> },
      { path: 'cost', element: <CostPage /> },
      { path: 'settings', element: <SettingsPage /> },
    ],
  },
])

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
)
