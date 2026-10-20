import { useState } from 'react'
import { AppShell } from './components/layout/AppShell'
import { ErrorNotice } from './components/common/ErrorNotice'
import { LoadingState } from './components/common/LoadingState'
import { useFinishers } from './hooks/useCatalog'
import { ExposurePage } from './pages/ExposurePage'

export default function App() {
  const finishers = useFinishers()
  const [selectedFinisherId, setSelectedFinisherId] = useState('')
  const companies = finishers.data || []
  const finisherId = selectedFinisherId || companies[0]?.id || ''

  return (
    <AppShell
      finishers={companies}
      finisherId={finisherId}
      onFinisherChange={setSelectedFinisherId}
    >
      {finishers.error && (
        <ErrorNotice message={finishers.error.message} onRetry={finishers.refetch} />
      )}
      {finishers.isLoading && <LoadingState>Loading finishers…</LoadingState>}
      {finisherId && <ExposurePage key={finisherId} finisherId={finisherId} />}
    </AppShell>
  )
}
