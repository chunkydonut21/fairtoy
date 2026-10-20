import { useCallback, useState } from 'react'
import { Alert, Title } from '@mantine/core'
import { ErrorNotice } from '../components/common/ErrorNotice'
import { LoadingState } from '../components/common/LoadingState'
import { CatalogPanel } from '../components/catalog/CatalogPanel'
import { ExposureSummary } from '../components/exposure/ExposureSummary'
import { FlagSupplierDialog } from '../components/suppliers/FlagSupplierDialog'
import { ResolveSupplierDialog } from '../components/suppliers/ResolveSupplierDialog'
import { ToyTraceDrawer } from '../components/toys/ToyTraceDrawer'
import { useOverview } from '../hooks/useCatalog'

const defaultView = { tab: 'toys', filter: 'all', search: '' }

export function ExposurePage({ finisherId }) {
  const { data: overview, isLoading, error, refetch } = useOverview(finisherId)
  const [view, setView] = useState(defaultView)
  const [selectedToyId, setSelectedToyId] = useState(null)
  const [flagTarget, setFlagTarget] = useState(null)
  const [resolveTarget, setResolveTarget] = useState(null)
  const [resolvedSupplier, setResolvedSupplier] = useState(null)
  const closeToy = useCallback(() => setSelectedToyId(null), [])
  const closeFlag = useCallback(() => setFlagTarget(null), [])
  const closeResolve = useCallback(() => setResolveTarget(null), [])

  function handleFlagSaved() {
    setFlagTarget(null)
    setResolvedSupplier(null)
    setView((current) => ({ ...current, filter: 'affected' }))
  }

  function handleResolveSaved() {
    setResolvedSupplier(resolveTarget.name)
    setResolveTarget(null)
    setView((current) => ({ ...current, filter: 'all' }))
  }

  return (
    <>
      <Title order={1} size="h3" mb="md">
        Catalog
      </Title>

      {error && <ErrorNotice message={error.message} onRetry={refetch} />}
      {isLoading && <LoadingState>Loading supply chain…</LoadingState>}
      {resolvedSupplier && (
        <Alert color="teal" mb="md" withCloseButton onClose={() => setResolvedSupplier(null)}>
          {resolvedSupplier} is no longer flagged. Toys affected only by this supplier are now
          marked clear.
        </Alert>
      )}
      {overview && (
        <>
          <ExposureSummary
            summary={overview.summary}
            onReviewSuppliers={() => setView({ tab: 'suppliers', filter: 'affected', search: '' })}
          />
          <CatalogPanel
            toys={overview.toys}
            suppliers={overview.suppliers}
            view={view}
            onViewChange={setView}
            onSelectToy={setSelectedToyId}
            onFlagSupplier={setFlagTarget}
            onResolveSupplier={setResolveTarget}
          />
        </>
      )}

      {selectedToyId && (
        <ToyTraceDrawer
          finisherId={finisherId}
          finisherName={overview?.finisher.name}
          toyId={selectedToyId}
          onClose={closeToy}
        />
      )}
      {flagTarget && (
        <FlagSupplierDialog
          finisherId={finisherId}
          supplier={flagTarget}
          onClose={closeFlag}
          onSaved={handleFlagSaved}
        />
      )}
      {resolveTarget && (
        <ResolveSupplierDialog
          finisherId={finisherId}
          supplier={resolveTarget}
          onClose={closeResolve}
          onSaved={handleResolveSaved}
        />
      )}
    </>
  )
}
