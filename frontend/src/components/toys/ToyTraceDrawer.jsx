import { Alert, Drawer, Group, Stack, Text, ThemeIcon, Title } from '@mantine/core'
import { IconCube, IconInfoCircle } from '@tabler/icons-react'
import { useToyDetail } from '../../hooks/useCatalog'
import { ErrorNotice } from '../common/ErrorNotice'
import { LoadingState } from '../common/LoadingState'
import { StatusBadge } from '../common/StatusBadge'
import { PartCard } from './PartCard'

export function ToyTraceDrawer({ finisherId, finisherName, toyId, onClose }) {
  const { data: toy, isLoading, error, refetch } = useToyDetail(finisherId, toyId)

  return (
    <Drawer
      opened
      onClose={onClose}
      title="Toy trace"
      position="right"
      size="min(100vw, 560px)"
      padding="xl"
      closeButtonProps={{ 'aria-label': 'Close toy detail' }}
    >
      {isLoading && <LoadingState>Loading trace…</LoadingState>}
      {error && <ErrorNotice message={error.message} onRetry={refetch} />}
      {toy && (
        <Stack gap="lg">
          <Group align="start" wrap="nowrap">
            <ThemeIcon color="blue" size={44} variant="light" radius="md">
              <IconCube size={24} />
            </ThemeIcon>
            <div>
              <Title order={2} size="h3">
                {toy.name}
              </Title>
              <Text size="xs" c="dimmed" mt={4}>
                {toy.id} · {finisherName}
              </Text>
            </div>
          </Group>
          <div>
            <StatusBadge affected={toy.affected} />
          </div>
          <Alert color={toy.affected ? 'orange' : 'teal'} icon={<IconInfoCircle size={18} />}>
            {toy.affected
              ? 'Flagged supplier sources appear in the part list below. Follow each row from this toy through its part and source factory.'
              : 'No supplier source for this toy is currently flagged.'}
          </Alert>
          <Group justify="space-between">
            <Text size="xs" fw={700} c="dimmed" tt="uppercase">
              Bill of materials
            </Text>
            <Text size="xs" c="dimmed">
              {toy.parts.length} parts
            </Text>
          </Group>
          <Stack gap="sm">
            {toy.parts.map((part) => (
              <PartCard key={part.id} part={part} />
            ))}
          </Stack>
        </Stack>
      )}
    </Drawer>
  )
}
