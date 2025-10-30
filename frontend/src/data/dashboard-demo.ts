export const dashboardDemo = {
  document_summary: {
    total_purchase_orders: 1,
    total_invoices: 1,
    total_documents: 2,
    total_value: 26316.56,
    average_invoice_value: 13113.28,
    linked_invoice_to_po_ratio: 1.0,
    unique_vendors: 1,
  },
  financial_summary: {
    avg_subtotal: 12597.4,
    avg_tax_amount: 1240.78,
    avg_discount: 1100.0,
    avg_total_amount: 13158.28,
    total_tax_paid: 2481.56,
    total_discount: 2200.0,
    effective_tax_rate: 9.85,
    effective_discount_rate: 8.73,
  },
  vendor_analytics: {
    vendor_count: 1,
    top_vendors_by_value: [
      { vendor: "Acme", count: 2, total_value: 26316.56 },
    ],
    avg_docs_per_vendor: 2,
  },
  discrepancy_insights: {
    total_comparisons: 1,
    avg_discrepancies_per_comparison: 10,
    most_recent_summary:
      "Multiple financial and administrative discrepancies were identified. The invoice exhibits significant line item mismatches (quantity and unit price) for Product 1, resulting in flags for over-billing and unit price variance. The stated subtotal and tax amounts differ from the PO. Furthermore, the Invoice contains internal calculation errors, as the stated total amount ($13,113.28) does not match the sum of its components ($13,233.28). Administrative issues include conflicting PO dates and a typo in the bill-to address.",
  },
  line_item_analysis: {
    unique_items: 3,
    top_items_by_value: [
      { item: "Product 1", qty: 0.0, total_value: 0.0 },
      { item: "Product 2", qty: 0.0, total_value: 0.0 },
      { item: "Service 1", qty: 0.0, total_value: 0.0 },
    ],
  },
  temporal_trends: {
    monthly_total_values: {
      "2024-01": 13113.28,
      "2024-04": 13203.28,
    },
    months_active: 2,
    first_month: "2024-04",
    last_month: "2024-01",
  },
  graphs: {
    documents: {
      document_type_distribution: [
        { label: "Purchase Orders", value: 1 },
        { label: "Invoices", value: 1 },
      ],
      document_value_overview: [
        { label: "Total Value", value: 26316.56 },
        { label: "Average Invoice Value", value: 13113.28 },
      ],
    },
    financials: {
      cost_composition: [
        { label: "Subtotal", value: 25194.8 },
        { label: "Tax", value: 2481.56 },
        { label: "Discount", value: -2200.0 },
      ],
      invoice_amount_distribution: [
        { x: "Acme", y: 13113.28 },
      ],
    },
    vendors: {
      top_vendors_chart: [
        { x: "Acme", y: 26316.56 },
      ],
      vendor_document_volume: [
        { x: "Acme", y: 2 },
      ],
    },
    discrepancies: {
      discrepancy_trend: [
        { x: 1, y: 10 },
      ],
    },
    line_items: {
      top_items_chart: [
        { x: "Product 1", y: 0.0 },
        { x: "Product 2", y: 0.0 },
        { x: "Service 1", y: 0.0 },
      ],
      top_items_qty: [
        { x: "Product 1", y: 0.0 },
        { x: "Product 2", y: 0.0 },
        { x: "Service 1", y: 0.0 },
      ],
    },
    temporal: {
      monthly_spending_trend: [
        { x: "2024-01", y: 13113.28 },
        { x: "2024-04", y: 13203.28 },
      ],
    },
  },
} as const;
