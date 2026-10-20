import { Badge } from '@mantine/core'
import { IconCircleFilled } from '@tabler/icons-react'

export function StatusBadge({ affected, flagged = false }) {
  const label = affected ? (flagged ? 'Flagged' : 'Affected') : 'Clear'

  return (
    <Badge
      color={affected ? 'orange' : 'teal'}
      variant="light"
      radius="sm"
      tt="none"
      leftSection={<IconCircleFilled size={6} />}
      data-status={affected ? 'affected' : 'clear'}
    >
      {label}
    </Badge>
  )
}
