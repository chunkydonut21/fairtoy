import { Badge, Group, Paper, Stack, Text, ThemeIcon } from '@mantine/core'
import { IconBuildingFactory2 } from '@tabler/icons-react'

export function PartCard({ part }) {
  return (
    <Paper p="md" withBorder data-exposed={part.affected} className="part-card">
      <Group justify="space-between" align="start" wrap="nowrap">
        <div>
          <Text size="sm" fw={600}>
            {part.name}
          </Text>
          <Text size="xs" c="dimmed">
            {part.id} · Qty {part.quantity}
          </Text>
        </div>
        {part.affected && (
          <Badge color="orange" variant="light" size="xs">
            Exposed
          </Badge>
        )}
      </Group>
      <Stack gap="sm" mt="md">
        {part.sources.map((source) => (
          <Group
            gap="sm"
            align="start"
            wrap="nowrap"
            key={`${source.supplier_id}-${source.factory_id}`}
          >
            <ThemeIcon size={28} variant="light" color={source.flagged_at ? 'orange' : 'teal'}>
              <IconBuildingFactory2 size={15} />
            </ThemeIcon>
            <div className="source-details">
              <Group gap="xs">
                <Text size="xs" fw={600}>
                  {source.supplier_name}
                </Text>
                {source.flagged_at && (
                  <Badge size="xs" color="orange" variant="light">
                    Flagged
                  </Badge>
                )}
              </Group>
              <Text size="xs" c="dimmed" mt={2}>
                {source.factory_name.replaceAll(' — ', ', ')}
              </Text>
              <Text size="xs" c="dimmed">
                {[source.city, source.country].filter(Boolean).join(', ')}
              </Text>
              {source.flagged_at && source.flag_reason && (
                <Text size="xs" c="orange.8" mt={4}>
                  Finding: {source.flag_reason}
                </Text>
              )}
            </div>
          </Group>
        ))}
      </Stack>
    </Paper>
  )
}
