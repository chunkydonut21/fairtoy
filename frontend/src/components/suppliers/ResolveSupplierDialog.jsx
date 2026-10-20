import { useState } from 'react'
import { Button, Group, Modal, Select, Stack, Text, Textarea } from '@mantine/core'
import { IconCheck } from '@tabler/icons-react'
import { useResolveFlag } from '../../hooks/useCatalog'
import { ErrorNotice } from '../common/ErrorNotice'

export function ResolveSupplierDialog({ finisherId, supplier, onClose, onSaved }) {
  const [outcome, setOutcome] = useState(null)
  const [note, setNote] = useState('')
  const { mutate, isPending: saving, error } = useResolveFlag(finisherId)

  function handleSubmit(event) {
    event.preventDefault()
    mutate({ flagId: supplier.flag.id, outcome, note }, { onSuccess: onSaved })
  }

  return (
    <Modal
      opened
      onClose={onClose}
      title={`Resolve ${supplier.name}`}
      centered
      closeOnClickOutside={!saving}
      closeOnEscape={!saving}
      closeButtonProps={{ disabled: saving, 'aria-label': 'Close resolution dialog' }}
    >
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            Resolve after affected toys have been recalled, or correct a flag entered in error. The
            original finding and your resolution will be kept.
          </Text>
          <Text size="sm">Original finding: {supplier.flag.reason}</Text>
          {error && <ErrorNotice message={error.message} />}
          <Select
            label="Resolution"
            placeholder="Choose a resolution"
            data={[
              { value: 'recalled', label: 'Affected toys recalled' },
              { value: 'flagged_in_error', label: 'Flag entered in error' },
            ]}
            value={outcome}
            onChange={setOutcome}
            required
            allowDeselect={false}
            disabled={saving}
            data-autofocus
          />
          <Textarea
            label="Resolution note"
            placeholder="Explain the resolution and include any reference"
            required
            minLength={3}
            maxLength={500}
            autosize
            minRows={3}
            value={note}
            onChange={(event) => setNote(event.target.value)}
            disabled={saving}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose} disabled={saving}>
              Cancel
            </Button>
            <Button
              type="submit"
              leftSection={<IconCheck size={16} />}
              loading={saving}
              disabled={!outcome || note.trim().length < 3}
            >
              Resolve supplier
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  )
}
