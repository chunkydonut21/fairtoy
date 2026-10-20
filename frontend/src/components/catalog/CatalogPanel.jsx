import { Badge, Paper, Tabs, Text } from '@mantine/core'
import { SupplierTable } from '../suppliers/SupplierTable'
import { ToyTable } from '../toys/ToyTable'
import { CatalogToolbar } from './CatalogToolbar'

function matchesFilter(item, view) {
  const matchesSearch = `${item.name} ${item.id}`.toLowerCase().includes(view.search.toLowerCase())
  const affected = item.affected ?? Boolean(item.flag)
  const matchesStatus = view.filter === 'all' || (view.filter === 'affected' ? affected : !affected)
  return matchesSearch && matchesStatus
}

export function CatalogPanel({
  toys,
  suppliers,
  view,
  onViewChange,
  onSelectToy,
  onFlagSupplier,
  onResolveSupplier,
}) {
  const isToyView = view.tab === 'toys'
  const items = isToyView ? toys : suppliers
  const visible = items.filter((item) => matchesFilter(item, view))

  return (
    <Paper id="catalog" withBorder className="catalog-panel">
      <Tabs value={view.tab} onChange={(tab) => onViewChange({ tab, filter: 'all', search: '' })}>
        <Tabs.List className="catalog-tabs">
          <Tabs.Tab
            value="toys"
            rightSection={
              <Badge color="gray" size="xs">
                {toys.length}
              </Badge>
            }
          >
            Toys
          </Tabs.Tab>
          <Tabs.Tab
            value="suppliers"
            rightSection={
              <Badge color="gray" size="xs">
                {suppliers.length}
              </Badge>
            }
          >
            Suppliers
          </Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value={view.tab}>
          <CatalogToolbar
            {...view}
            onSearchChange={(search) => onViewChange({ ...view, search })}
            onFilterChange={(filter) => onViewChange({ ...view, filter })}
          />
          {isToyView ? (
            <ToyTable toys={visible} onSelect={onSelectToy} />
          ) : (
            <SupplierTable
              suppliers={visible}
              onFlag={onFlagSupplier}
              onResolve={onResolveSupplier}
            />
          )}
          <Text size="xs" c="dimmed" px="lg" py="md">
            Showing {visible.length} of {items.length} {view.tab}
          </Text>
        </Tabs.Panel>
      </Tabs>
    </Paper>
  )
}
