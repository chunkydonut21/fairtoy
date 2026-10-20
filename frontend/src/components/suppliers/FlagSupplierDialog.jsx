import { useState } from 'react'
import { Button, Group, Modal, Stack, Text, Textarea } from '@mantine/core'
import { IconFlag } from '@tabler/icons-react'
import { useFlagSupplier } from '../../hooks/useCatalog'
import { ErrorNotice } from '../common/ErrorNotice'

export function FlagSupplierDialog({ finisherId, supplier, onClose, onSaved }) {
  const [reason, setReason] = useState('')
  const { mutate, isPending: saving, error } = useFlagSupplier(finisherId)

  function handleSubmit(event) {
    event.preventDefault()
    mutate({ supplierId: supplier.id, reason }, { onSuccess: onSaved })
  }

  return (
    <Modal
      opened
      onClose={onClose}
      title={`Flag ${supplier.name}`}
      centered
      closeOnClickOutside={!saving}
      closeOnEscape={!saving}
      closeButtonProps={{ disabled: saving, 'aria-label': 'Close flag dialog' }}
    >
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            This marks the supplier as a child labor concern for this finisher and updates exposure
            for every toy in this catalog that uses its parts. The flag persists across restarts.
          </Text>
          {error && <ErrorNotice message={error.message} />}
          <Textarea
            label="Reason for flagging"
            placeholder="Describe the finding or source of concern"
            required
            minLength={3}
            maxLength={500}
            autosize
            minRows={4}
            data-autofocus
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            disabled={saving}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose} disabled={saving}>
              Cancel
            </Button>
            <Button
              type="submit"
              color="orange"
              leftSection={<IconFlag size={16} />}
              loading={saving}
              disabled={reason.trim().length < 3}
            >
              Flag supplier
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  )
}
