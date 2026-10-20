import { Button, Group, Table, Text, ThemeIcon, VisuallyHidden } from '@mantine/core'
import { IconArrowRight, IconCube } from '@tabler/icons-react'
import { StatusBadge } from '../common/StatusBadge'

export function ToyTable({ toys, onSelect }) {
  return (
    <Table.ScrollContainer minWidth={600}>
      <Table
        aria-label="Toys"
        highlightOnHover
        verticalSpacing="md"
        horizontalSpacing="lg"
        className="catalog-table"
      >
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Toy</Table.Th>
            <Table.Th>Parts</Table.Th>
            <Table.Th>Exposure</Table.Th>
            <Table.Th>
              <VisuallyHidden>Action</VisuallyHidden>
            </Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {toys.map((toy) => (
            <Table.Tr key={toy.id}>
              <Table.Td>
                <Group gap="sm" wrap="nowrap">
                  <ThemeIcon variant="light" color="blue" size={34} radius="md">
                    <IconCube size={18} />
                  </ThemeIcon>
                  <div>
                    <Text size="sm" fw={600}>
                      {toy.name}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {toy.id}
                    </Text>
                  </div>
                </Group>
              </Table.Td>
              <Table.Td>
                <Text size="sm" c="dimmed">
                  {toy.part_count} parts
                </Text>
              </Table.Td>
              <Table.Td>
                <StatusBadge affected={toy.affected} />
              </Table.Td>
              <Table.Td align="right">
                <Button
                  variant="subtle"
                  size="xs"
                  aria-label={`View ${toy.name} trace`}
                  rightSection={<IconArrowRight size={15} />}
                  onClick={() => onSelect(toy.id)}
                >
                  View trace
                </Button>
              </Table.Td>
            </Table.Tr>
          ))}
          {!toys.length && (
            <Table.Tr>
              <Table.Td colSpan={4}>
                <Text ta="center" c="dimmed" size="sm" py="xl">
                  No toys match this view.
                </Text>
              </Table.Td>
            </Table.Tr>
          )}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  )
}
