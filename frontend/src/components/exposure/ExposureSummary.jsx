import { Alert, Button, Group, Text } from '@mantine/core'

function SummaryItem({ id, label, value }) {
  return (
    <Group gap={6} wrap="nowrap" data-metric={id}>
      <Text component="dt" size="sm" c="dimmed">
        {label}
      </Text>
      <Text component="dd" size="sm" fw={600} m={0}>
        {value}
      </Text>
    </Group>
  )
}

export function ExposureSummary({ summary, onReviewSuppliers }) {
  return (
    <>
      <Group component="dl" gap="lg" className="catalog-summary">
        <SummaryItem id="toys" label="Toys" value={summary.toy_count} />
        <SummaryItem id="suppliers" label="Suppliers" value={summary.supplier_count} />
        <SummaryItem id="affected" label="Affected toys" value={summary.affected_toy_count} />
        <SummaryItem
          id="flagged"
          label="Flagged suppliers"
          value={summary.flagged_supplier_count}
        />
      </Group>
      {summary.flagged_supplier_count > 0 && (
        <Alert color="orange" mb="md">
          <Group justify="space-between" gap="sm">
            <Text size="sm">
              {summary.affected_toy_count} toys have parts linked to a flagged supplier. Review them
              for recall.
            </Text>
            <Button variant="light" color="orange" size="xs" onClick={onReviewSuppliers}>
              Review flagged suppliers
            </Button>
          </Group>
        </Alert>
      )}
    </>
  )
}
