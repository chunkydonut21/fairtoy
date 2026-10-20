import { Center, Group, Loader, Text } from '@mantine/core'

export function LoadingState({ children }) {
  return (
    <Center py="xl" role="status">
      <Group gap="sm">
        <Loader size="sm" />
        <Text size="sm" c="dimmed">
          {children}
        </Text>
      </Group>
    </Center>
  )
}
