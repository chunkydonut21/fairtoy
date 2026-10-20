import { Box, Container, Group, Select, Text } from '@mantine/core'

export function AppShell({ finishers, finisherId, onFinisherChange, children }) {
  return (
    <>
      <Box component="header" className="app-header">
        <Container size="lg">
          <Group justify="space-between" gap="md">
            <Text size="lg" fw={700}>
              FairToy
            </Text>
            <Group className="finisher-picker" gap="sm" wrap="nowrap">
              <Text component="label" htmlFor="finisher" size="sm" c="dimmed">
                Finisher
              </Text>
              <Select
                id="finisher"
                className="finisher-select"
                aria-label="Select finisher"
                value={finisherId || null}
                data={finishers.map((finisher) => ({ value: finisher.id, label: finisher.name }))}
                onChange={(value) => {
                  if (value) onFinisherChange(value)
                }}
                allowDeselect={false}
                size="sm"
              />
            </Group>
          </Group>
        </Container>
      </Box>
      <Container component="main" size="lg" py="lg">
        {children}
      </Container>
    </>
  )
}
