import { Group, SegmentedControl, TextInput } from '@mantine/core'
import { IconSearch } from '@tabler/icons-react'

export function CatalogToolbar({ tab, search, filter, onSearchChange, onFilterChange }) {
  return (
    <Group justify="space-between" p="lg" gap="sm">
      <TextInput
        className="catalog-search"
        aria-label={`Search ${tab}`}
        placeholder={`Search ${tab} by name or ID`}
        leftSection={<IconSearch size={16} />}
        value={search}
        onChange={(event) => onSearchChange(event.target.value)}
        size="sm"
      />
      <SegmentedControl
        aria-label="Filter by status"
        role="radiogroup"
        size="sm"
        value={filter}
        onChange={onFilterChange}
        data={[
          { value: 'all', label: 'All' },
          { value: 'affected', label: tab === 'toys' ? 'Affected' : 'Flagged' },
          { value: 'clear', label: 'Clear' },
        ]}
      />
    </Group>
  )
}
