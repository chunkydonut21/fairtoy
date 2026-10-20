async function request(path, options = {}) {
  const response = await fetch(`/api${path}`, options)
  if (!response.headers.get('content-type')?.includes('application/json')) {
    throw new Error(
      response.ok
        ? 'The server returned an unexpected response.'
        : `Request failed (${response.status}). Please try again.`,
    )
  }
  const body = await response.json()

  if (!response.ok) {
    const validation = Array.isArray(body.detail)
      ? body.detail.map((issue) => issue.msg).join('; ')
      : body.detail
    throw new Error(body.error || validation || 'Request failed')
  }

  return body
}

export function get(path, signal) {
  return request(path, { signal })
}

export function flagSupplier(finisherId, supplierId, reason) {
  const finisher = encodeURIComponent(finisherId)
  return request(`/finishers/${finisher}/suppliers/${encodeURIComponent(supplierId)}/flags`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  })
}

export function resolveFlag(finisherId, flagId, outcome, note) {
  return request(`/finishers/${encodeURIComponent(finisherId)}/flags/${flagId}/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ outcome, note }),
  })
}
