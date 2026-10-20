import { Button, Group, Stack, Table, Text, ThemeIcon } from '@mantine/core'
import { IconBuildingFactory2, IconCheck, IconFlag } from '@tabler/icons-react'
import { StatusBadge } from '../common/StatusBadge'

export function SupplierTable({ suppliers, onFlag, onResolve }) {
  return (
    <Table.ScrollContainer minWidth={700}>
      <Table
        aria-label="Suppliers"
        highlightOnHover
        verticalSpacing="md"
        horizontalSpacing="lg"
        className="catalog-table"
      >
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Supplier</Table.Th>
            <Table.Th>Reach</Table.Th>
            <Table.Th>Status</Table.Th>
            <Table.Th>Action</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {suppliers.map((supplier) => (
            <Table.Tr key={supplier.id}>
              <Table.Td>
                <Group gap="sm" wrap="nowrap">
                  <ThemeIcon variant="light" size={34} radius="md">
                    <IconBuildingFactory2 size={18} />
                  </ThemeIcon>
                  <div>
                    <Text size="sm" fw={600}>
                      {supplier.name}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {supplier.id} · {supplier.country}
                    </Text>
                  </div>
                </Group>
              </Table.Td>
              <Table.Td>
                <Text size="sm" c="dimmed">
                  {supplier.toy_count} toys · {supplier.part_count} parts
                </Text>
              </Table.Td>
              <Table.Td>
                <StatusBadge affected={Boolean(supplier.flag)} flagged />
              </Table.Td>
              <Table.Td>
                {supplier.flag ? (
                  <Stack gap={4} align="start">
                    <Button
                      variant="light"
                      size="xs"
                      leftSection={<IconCheck size={14} />}
                      onClick={() => onResolve(supplier)}
                    >
                      Resolve
                    </Button>
                    <Text size="xs" c="dimmed">
                      Flagged {new Date(supplier.flag.flagged_at).toLocaleDateString()}
                    </Text>
                  </Stack>
                ) : (
                  <Button
                    variant="light"
                    color="orange"
                    size="xs"
                    leftSection={<IconFlag size={14} />}
                    onClick={() => onFlag(supplier)}
                  >
                    Flag supplier
                  </Button>
                )}
              </Table.Td>
            </Table.Tr>
          ))}
          {!suppliers.length && (
            <Table.Tr>
              <Table.Td colSpan={4}>
                <Text ta="center" c="dimmed" size="sm" py="xl">
                  No suppliers match this view.
                </Text>
              </Table.Td>
            </Table.Tr>
          )}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  )
}
