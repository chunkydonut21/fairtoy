import { Alert, Button, Group, Text } from '@mantine/core'
import { IconAlertCircle } from '@tabler/icons-react'

export function ErrorNotice({ message, onRetry }) {
  return (
    <Alert color="red" icon={<IconAlertCircle size={18} />} role="alert" mb="md">
      <Group justify="space-between" align="center">
        <Text size="sm">{message}</Text>
        {onRetry && (
          <Button variant="light" color="red" size="xs" onClick={onRetry}>
            Try again
          </Button>
        )}
      </Group>
    </Alert>
  )
}
