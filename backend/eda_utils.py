import statistics
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import PurchaseOrderDB, InvoiceDB, CompareResponseDB
from typing import Dict, Any, List


# ---------------------- HELPER ----------------------
def safe_mean(values: List[float]) -> float:
    """Return mean safely even if list is empty."""
    return round(statistics.mean(values), 2) if values else 0.0


def to_float(value):
    try:
        return float(value) if value is not None else 0.0
    except:
        return 0.0


# ---------------------- MAIN FUNCTION ----------------------
async def get_user_eda(session: AsyncSession, user_id: int) -> Dict[str, Any]:
    """
    Compute EDA metrics for a given user across Purchase Orders, Invoices,
    Comparisons, and Line Items.
    Categories covered:
      1. Document Summary
      2. Financial Insights
      3. Vendor Analytics
      5. Discrepancy Insights
      6. Line Item-Level Insights
      7. Temporal Trends
    """

    # ---------------------- LOAD DATA ----------------------
    po_query = await session.execute(
        select(PurchaseOrderDB).where(PurchaseOrderDB.created_by == user_id)
    )
    inv_query = await session.execute(
        select(InvoiceDB).where(InvoiceDB.created_by == user_id)
    )
    comp_query = await session.execute(
        select(CompareResponseDB).where(CompareResponseDB.created_by == user_id)
    )

    pos = po_query.scalars().all()
    invoices = inv_query.scalars().all()
    comparisons = comp_query.scalars().all()

    # Flatten totals for numeric analysis
    all_docs = pos + invoices

    # ---------------------- 1. DOCUMENT SUMMARY ----------------------
    total_pos = len(pos)
    total_invoices = len(invoices)
    total_docs = total_pos + total_invoices
    total_value = sum(to_float(d.total_amount) for d in all_docs)
    avg_invoice_value = safe_mean([to_float(i.total_amount) for i in invoices])
    unique_vendors = len(set(d.vendor_name for d in all_docs if d.vendor_name))
    invoice_po_links = sum(1 for i in invoices if i.po_number)

    document_summary = {
        "total_purchase_orders": total_pos,
        "total_invoices": total_invoices,
        "total_documents": total_docs,
        "total_value": total_value,
        "average_invoice_value": avg_invoice_value,
        "linked_invoice_to_po_ratio": round(invoice_po_links / total_invoices, 2)
        if total_invoices else 0,
        "unique_vendors": unique_vendors,
    }

    document_graphs = {
        "document_type_distribution": [
            {"label": "Purchase Orders", "value": total_pos},
            {"label": "Invoices", "value": total_invoices},
        ],
        "document_value_overview": [
            {"label": "Total Value", "value": total_value},
            {"label": "Average Invoice Value", "value": avg_invoice_value},
        ],
    }

    # ---------------------- 2. FINANCIAL INSIGHTS ----------------------
    subtotals = [to_float(d.subtotal) for d in all_docs]
    taxes = [to_float(d.tax_amount) for d in all_docs]
    discounts = [to_float(d.discount) for d in all_docs if d.discount]
    totals = [to_float(d.total_amount) for d in all_docs]

    financial_summary = {
        "avg_subtotal": safe_mean(subtotals),
        "avg_tax_amount": safe_mean(taxes),
        "avg_discount": safe_mean(discounts),
        "avg_total_amount": safe_mean(totals),
        "total_tax_paid": sum(taxes),
        "total_discount": sum(discounts),
        "effective_tax_rate": round(
            (sum(taxes) / sum(subtotals) * 100) if sum(subtotals) else 0, 2
        ),
        "effective_discount_rate": round(
            (sum(discounts) / sum(subtotals) * 100) if sum(subtotals) else 0, 2
        ),
    }

    financial_graphs = {
        "cost_composition": [
            {"label": "Subtotal", "value": sum(subtotals)},
            {"label": "Tax", "value": sum(taxes)},
            {"label": "Discount", "value": -sum(discounts)},
        ],
        "invoice_amount_distribution": [
            {"x": i.vendor_name or "Unknown", "y": to_float(i.total_amount)}
            for i in invoices if i.total_amount
        ],
    }

    # ---------------------- 3. VENDOR ANALYTICS ----------------------
    vendor_data = {}
    for doc in all_docs:
        if not doc.vendor_name:
            continue
        name = doc.vendor_name
        vendor_data.setdefault(name, {"count": 0, "total_value": 0.0})
        vendor_data[name]["count"] += 1
        vendor_data[name]["total_value"] += to_float(doc.total_amount)

    top_vendors = sorted(
        [{"vendor": k, **v} for k, v in vendor_data.items()],
        key=lambda x: x["total_value"],
        reverse=True,
    )[:10]

    vendor_analytics = {
        "vendor_count": len(vendor_data),
        "top_vendors_by_value": top_vendors,
        "avg_docs_per_vendor": safe_mean([v["count"] for v in vendor_data.values()]),
    }

    vendor_graphs = {
        "top_vendors_chart": [
            {"x": v["vendor"], "y": v["total_value"]} for v in top_vendors
        ],
        "vendor_document_volume": [
            {"x": v["vendor"], "y": v["count"]} for v in top_vendors
        ],
    }

    # ---------------------- 5. DISCREPANCY INSIGHTS ----------------------
    discrepancy_insights = {
        "total_comparisons": len(comparisons),
        "avg_discrepancies_per_comparison": safe_mean(
            [len(c.discrepancy) for c in comparisons if isinstance(c.discrepancy, list)]
        ),
        "most_recent_summary": comparisons[-1].summary if comparisons else None,
    }

    discrepancy_graphs = {
        "discrepancy_trend": [
            {
                "x": c.id,
                "y": len(c.discrepancy) if isinstance(c.discrepancy, list) else 0,
            }
            for c in comparisons
        ]
    }

    # ---------------------- 6. LINE ITEM ANALYSIS ----------------------
    item_counts = {}
    for doc in all_docs:
        if not doc.line_items:
            continue
        for item in doc.line_items:
            name = item.get("item") or item.get("description")
            if not name:
                continue
            qty = to_float(item.get("qty", 0))
            price = to_float(item.get("price", 0))
            if name not in item_counts:
                item_counts[name] = {"qty": 0, "total_value": 0}
            item_counts[name]["qty"] += qty
            item_counts[name]["total_value"] += qty * price

    top_items = sorted(
        [{"item": k, **v} for k, v in item_counts.items()],
        key=lambda x: x["total_value"],
        reverse=True,
    )[:10]

    line_item_analysis = {
        "unique_items": len(item_counts),
        "top_items_by_value": top_items,
    }

    line_item_graphs = {
        "top_items_chart": [
            {"x": i["item"], "y": i["total_value"]} for i in top_items
        ],
        "top_items_qty": [
            {"x": i["item"], "y": i["qty"]} for i in top_items
        ],
    }

    # ---------------------- 7. TEMPORAL TRENDS ----------------------
    def parse_date(date_str):
        if not date_str:
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(date_str, fmt).date()
            except:
                continue
        return None

    monthly_totals = {}
    for doc in all_docs:
        date_field = parse_date(doc.invoice_date or doc.po_date)
        if not date_field:
            continue
        month_key = date_field.strftime("%Y-%m")
        monthly_totals[month_key] = monthly_totals.get(month_key, 0) + to_float(
            doc.total_amount
        )

    temporal_trends = {
        "monthly_total_values": dict(sorted(monthly_totals.items())),
        "months_active": len(monthly_totals),
        "first_month": next(iter(monthly_totals.keys()), None),
        "last_month": next(reversed(monthly_totals.keys()), None),
    }

    temporal_graphs = {
        "monthly_spending_trend": [
            {"x": month, "y": value}
            for month, value in sorted(monthly_totals.items())
        ]
    }

    # ---------------------- COMBINE ALL ----------------------
    eda_summary = {
        "document_summary": document_summary,
        "financial_summary": financial_summary,
        "vendor_analytics": vendor_analytics,
        "discrepancy_insights": discrepancy_insights,
        "line_item_analysis": line_item_analysis,
        "temporal_trends": temporal_trends,
        # Graphs section for frontend visualizations
        "graphs": {
            "documents": document_graphs,
            "financials": financial_graphs,
            "vendors": vendor_graphs,
            "discrepancies": discrepancy_graphs,
            "line_items": line_item_graphs,
            "temporal": temporal_graphs,
        },
    }

    return eda_summary
