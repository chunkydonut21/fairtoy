import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { flagSupplier, get, resolveFlag } from '../api/client'

const catalogKeys = {
  finisher: (finisherId) => ['catalog', finisherId],
  overview: (finisherId) => ['catalog', finisherId, 'overview'],
  toy: (finisherId, toyId) => ['catalog', finisherId, 'toy', toyId],
}

export function useFinishers() {
  return useQuery({
    queryKey: ['finishers'],
    queryFn: ({ signal }) => get('/finishers', signal),
  })
}

export function useOverview(finisherId) {
  return useQuery({
    queryKey: catalogKeys.overview(finisherId),
    queryFn: ({ signal }) => get(`/finishers/${encodeURIComponent(finisherId)}/overview`, signal),
    enabled: Boolean(finisherId),
  })
}

export function useToyDetail(finisherId, toyId) {
  return useQuery({
    queryKey: catalogKeys.toy(finisherId, toyId),
    queryFn: ({ signal }) =>
      get(`/finishers/${encodeURIComponent(finisherId)}/toys/${encodeURIComponent(toyId)}`, signal),
    enabled: Boolean(finisherId && toyId),
  })
}

// A flag belongs to one finisher, so only that finisher's overview and toy traces change.
// They are refetched after failures too: a 409 means this view was out of date.
function useFlagMutation(finisherId, mutationFn) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn,
    onSettled: () => queryClient.invalidateQueries({ queryKey: catalogKeys.finisher(finisherId) }),
  })
}

export function useFlagSupplier(finisherId) {
  return useFlagMutation(finisherId, ({ supplierId, reason }) =>
    flagSupplier(finisherId, supplierId, reason),
  )
}

export function useResolveFlag(finisherId) {
  return useFlagMutation(finisherId, ({ flagId, outcome, note }) =>
    resolveFlag(finisherId, flagId, outcome, note),
  )
}
