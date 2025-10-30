# discrepancy_utils.py
from decimal import Decimal
from typing import Dict, Any, Tuple, List


# --------------------------------------------------------------------
# Helper utilities
# --------------------------------------------------------------------
def to_decimal(x) -> Decimal:
    try:
        return Decimal(str(x or 0))
    except Exception:
        return Decimal(0)


def approx_equal(a: Decimal, b: Decimal, tol: Decimal = Decimal("0.01")) -> bool:
    return abs(a - b) <= tol


def compute_subtotal_from_lines(lines: List[Dict[str, Any]]) -> Decimal:
    return sum(
        to_decimal(li.get("quantity")) * to_decimal(li.get("unit_price"))
        for li in lines
        if li.get("quantity") is not None and li.get("unit_price") is not None
    )


# --------------------------------------------------------------------
# Category 1: Quantity Discrepancies
# --------------------------------------------------------------------
def check_quantity_discrepancies(po: Dict[str, Any], inv: Dict[str, Any]) -> Tuple[Dict[str, int], int]:
    flags = {
        "Over-billing on quantity": 0,
        "Under-billing on quantity": 0,
        "Unit conversion errors": 0,
        "Partial shipments not reflected": 0,
    }

    po_qty_total = sum(to_decimal(i.get("quantity")) for i in po.get("line_items", []))
    inv_qty_total = sum(to_decimal(i.get("quantity")) for i in inv.get("line_items", []))

    if inv_qty_total > po_qty_total:
        flags["Over-billing on quantity"] = 1
    elif inv_qty_total < po_qty_total:
        flags["Under-billing on quantity"] = 1

    # Partial shipment
    if po.get("requires_shipment") and not inv.get("delivery_date"):
        flags["Partial shipments not reflected"] = 1

    category_score = sum(flags.values())
    return flags, category_score


# --------------------------------------------------------------------
# Category 2: Price Discrepancies
# --------------------------------------------------------------------
def check_price_discrepancies(po: Dict[str, Any], inv: Dict[str, Any]) -> Tuple[Dict[str, int], int]:
    flags = {
        "Unit price variance": 0,
        "Missing discounts": 0,
        "Price tier mismatches": 0,
        "Currency conversion errors": 0,
        "Unauthorized price increases": 0,
    }

    po_lines = po.get("line_items", []) or []
    inv_lines = inv.get("line_items", []) or []

    # 1️⃣ Unit price variance / unauthorized price increase
    for po_li, inv_li in zip(po_lines, inv_lines):
        po_up = to_decimal(po_li.get("unit_price"))
        inv_up = to_decimal(inv_li.get("unit_price"))
        if po_up and inv_up and not approx_equal(po_up, inv_up, tol=abs(po_up) * Decimal("0.01")):
            flags["Unit price variance"] = 1
            if inv_up > po_up:
                flags["Unauthorized price increases"] = 1

    # 2️⃣ Missing discounts: use model fields directly
    po_discount = to_decimal(po.get("discount")) or to_decimal(po.get("discount_percent"))
    inv_discount = to_decimal(inv.get("discount")) or to_decimal(inv.get("discount_percent"))
    if po_discount > 0 and inv_discount == 0:
        flags["Missing discounts"] = 1

    # 3️⃣ Price tier mismatch (≥20% difference)
    for po_li, inv_li in zip(po_lines, inv_lines):
        po_up = to_decimal(po_li.get("unit_price"))
        inv_up = to_decimal(inv_li.get("unit_price"))
        if po_up > 0:
            diff = abs(inv_up - po_up) / po_up
            if diff >= Decimal("0.20"):
                flags["Price tier mismatches"] = 1
                break

    # 4️⃣ Currency conversion errors (large ratio)
    po_total = to_decimal(po.get("total_amount"))
    inv_total = to_decimal(inv.get("total_amount"))
    if po_total and inv_total:
        ratio = po_total / inv_total if inv_total != 0 else Decimal(0)
        if ratio > Decimal("5") or ratio < Decimal("0.2"):
            flags["Currency conversion errors"] = 1

    return flags, sum(flags.values())


# --------------------------------------------------------------------
# Category 3: Tax and Calculation Errors
# --------------------------------------------------------------------
def check_tax_calculation_errors(po, inv):
    flags = {
        "Incorrect tax rates": 0,
        "Calculation errors": 0,
        "Duplicate tax application": 0,
        "Missing tax details": 0,
        "Tax on exempt items": 0,
        "Surcharge miscalculations": 0,
    }

    po_tax = to_decimal(po.get("tax_amount"))
    inv_tax = to_decimal(inv.get("tax_amount"))
    subtotal = to_decimal(inv.get("subtotal"))
    if subtotal and inv_tax and po_tax and not approx_equal(inv_tax, po_tax, tol=Decimal("0.5")):
        flags["Incorrect tax rates"] = 1

    computed_total = subtotal + inv_tax - to_decimal(inv.get("discount"))
    if not approx_equal(computed_total, to_decimal(inv.get("total_amount")), tol=Decimal("0.5")):
        flags["Calculation errors"] = 1

    if inv.get("tax_id") in (None, "", "NA"):
        flags["Missing tax details"] = 1

    # Tax on exempt items
    for li in inv.get("line_items", []):
        if li.get("tax_exempt") and inv_tax > 0:
            flags["Tax on exempt items"] = 1
            break

    # Surcharge miscalculations
    expected_surcharge = to_decimal(inv.get("freight")) + to_decimal(inv.get("handling"))
    if to_decimal(inv.get("surcharge")) and not approx_equal(expected_surcharge, to_decimal(inv.get("surcharge")), tol=Decimal("1.0")):
        flags["Surcharge miscalculations"] = 1

    return flags, sum(flags.values())


# --------------------------------------------------------------------
# Category 4: Duplicate Invoices
# --------------------------------------------------------------------
def check_duplicate_invoices(inv, other_invoices: List[Dict[str, Any]]):
    flags = {
        "Exact duplicates": 0,
        "Near-duplicates": 0,
        "Cumulative vs. incremental overlaps": 0,
        "System-generated duplicates": 0,
    }

    inv_id = inv.get("invoice_id")
    inv_total = to_decimal(inv.get("total_amount"))

    for other in other_invoices or []:
        if other.get("invoice_id") == inv_id:
            flags["Exact duplicates"] = 1
        elif (
            other.get("vendor_name") == inv.get("vendor_name")
            and abs(to_decimal(other.get("total_amount")) - inv_total) <= Decimal("1.0")
        ):
            flags["Near-duplicates"] = 1

    return flags, sum(flags.values())


# --------------------------------------------------------------------
# Category 5: Missing / Incomplete Data
# --------------------------------------------------------------------
def check_missing_incomplete_data(inv):
    flags = {
        "Missing PO reference": 0,
        "Missing line item details": 0,
        "Missing vendor info": 0,
        "Missing payment terms": 0,
        "Missing tax details": 0,
        "Missing invoice date": 0,
        "Missing delivery information": 0,
    }

    if not inv.get("po_number"):
        flags["Missing PO reference"] = 1
    if not inv.get("line_items"):
        flags["Missing line item details"] = 1
    if not inv.get("vendor_name"):
        flags["Missing vendor info"] = 1
    if not inv.get("payment_terms"):
        flags["Missing payment terms"] = 1
    if not inv.get("tax_id"):
        flags["Missing tax details"] = 1
    if not inv.get("invoice_date"):
        flags["Missing invoice date"] = 1
    if not inv.get("delivery_note") and inv.get("requires_shipment"):
        flags["Missing delivery information"] = 1

    return flags, sum(flags.values())


# --------------------------------------------------------------------
# Category 6: Unauthorized Charges
# --------------------------------------------------------------------
def check_unauthorized_charges(po, inv):
    flags = {
        "Freight charges not in PO": 0,
        "Handling charges": 0,
        "Cold chain surcharges": 0,
        "Expedited delivery fees": 0,
        "Tariffs/customs": 0,
        "Service charges": 0,
    }

    charge_fields = ["freight", "handling", "cold_chain_surcharge", "expedited_fee", "tariff", "customs", "service_charge"]
    for field in charge_fields:
        po_val, inv_val = to_decimal(po.get(field)), to_decimal(inv.get(field))
        if inv_val > 0 and po_val == 0:
            flag_name = field.replace("_", " ").title()
            # match field to specific flag
            for k in flags.keys():
                if field.split("_")[0] in k.lower():
                    flags[k] = 1
                    break
    return flags, sum(flags.values())


# --------------------------------------------------------------------
# Category 7: Line Item Description Mismatches
# --------------------------------------------------------------------
def check_line_item_description_mismatches(po, inv):
    flags = {
        "Description text mismatches": 0,
        "Specification mismatches": 0,
        "Brand differences": 0,
        "Wrong product": 0,
    }

    for po_li, inv_li in zip(po.get("line_items", []), inv.get("line_items", [])):
        if po_li.get("description") and inv_li.get("description") and po_li["description"].strip().lower() != inv_li["description"].strip().lower():
            flags["Description text mismatches"] = 1
        if po_li.get("spec") and inv_li.get("spec") and po_li["spec"] != inv_li["spec"]:
            flags["Specification mismatches"] = 1
        if po_li.get("brand") and inv_li.get("brand") and po_li["brand"] != inv_li["brand"]:
            flags["Brand differences"] = 1
        if po_li.get("part_number") and inv_li.get("part_number") and po_li["part_number"] != inv_li["part_number"]:
            flags["Wrong product"] = 1

    return flags, sum(flags.values())


# --------------------------------------------------------------------
# Category 8: Documentation & Reference Errors
# --------------------------------------------------------------------
def check_documentation_reference_errors(po, inv):
    flags = {
        "Wrong PO number": 0,
        "Incorrect cost center": 0,
        "Wrong service dates": 0,
        "Conflicting dates": 0,
        "Wrong bill-to address": 0,
        "Vendor mismatches": 0,
    }

    if po.get("po_number") and inv.get("po_number") and po["po_number"] != inv["po_number"]:
        flags["Wrong PO number"] = 1
    if po.get("cost_center") and inv.get("cost_center") and po["cost_center"] != inv["cost_center"]:
        flags["Incorrect cost center"] = 1
    if po.get("service_from") and inv.get("service_from") and po["service_from"] != inv["service_from"]:
        flags["Wrong service dates"] = 1
    if po.get("bill_to") and inv.get("bill_to") and po["bill_to"] != inv["bill_to"]:
        flags["Wrong bill-to address"] = 1
    if po.get("vendor_name") and inv.get("vendor_name") and po["vendor_name"] != inv["vendor_name"]:
        flags["Vendor mismatches"] = 1

    if po.get("po_date") and inv.get("invoice_date") and inv["invoice_date"] < po["po_date"]:
        flags["Conflicting dates"] = 1

    return flags, sum(flags.values())


# --------------------------------------------------------------------
# Category 9: Data Entry & Formatting Errors
# --------------------------------------------------------------------
def check_data_entry_formatting_errors(inv):
    flags = {
        "Transposition errors": 0,
        "Decimal point errors": 0,
        "Date format inconsistency": 0,
        "Currency confusion": 0,
        "Typing errors": 0,
    }

    # Example heuristic: decimal errors if any line total != qty*unit_price
    for li in inv.get("line_items", []):
        qty, up, total = to_decimal(li.get("quantity")), to_decimal(li.get("unit_price")), to_decimal(li.get("total"))
        if qty * up != total:
            flags["Decimal point errors"] = 1

    return flags, sum(flags.values())


# --------------------------------------------------------------------
# Category 10: Timing Issues
# --------------------------------------------------------------------
def check_timing_issues(inv):
    flags = {
        "Late invoice submission": 0,
        "Back-dated invoices": 0,
        "Service period overlaps": 0,
    }

    if inv.get("invoice_date") and inv.get("delivery_date"):
        if inv["invoice_date"] > inv["delivery_date"]:
            flags["Late invoice submission"] = 1
    if inv.get("service_from") and inv.get("service_to") and inv["service_from"] > inv["service_to"]:
        flags["Back-dated invoices"] = 1

    return flags, sum(flags.values())


# --------------------------------------------------------------------
# Category 11: Calculation Errors
# --------------------------------------------------------------------
def check_calculation_errors(inv):
    flags = {
        "Line total calculation errors": 0,
        "Subtotal mismatches": 0,
        "Invoice total errors": 0,
        "Discount calculation errors": 0,
        "Rounding error accumulation": 0,
    }

    subtotal_from_lines = compute_subtotal_from_lines(inv.get("line_items", []))
    if not approx_equal(subtotal_from_lines, to_decimal(inv.get("subtotal")), tol=Decimal("1.0")):
        flags["Subtotal mismatches"] = 1

    calc_total = to_decimal(inv.get("subtotal")) + to_decimal(inv.get("tax_amount")) - to_decimal(inv.get("discount"))
    if not approx_equal(calc_total, to_decimal(inv.get("total_amount")), tol=Decimal("1.0")):
        flags["Invoice total errors"] = 1

    return flags, sum(flags.values())


# --------------------------------------------------------------------
# Category 12: Authorization & Approval Errors
# --------------------------------------------------------------------
def check_authorization_approval_errors(po, inv):
    flags = {
        "Line items not in PO": 0,
        "Missing change orders": 0,
        "Services not delivered": 0,
    }

    po_descs = {li.get("description") for li in po.get("line_items", [])}
    for inv_li in inv.get("line_items", []):
        if inv_li.get("description") not in po_descs:
            flags["Line items not in PO"] = 1

    if to_decimal(inv.get("total_amount")) > to_decimal(po.get("total_amount")) * Decimal("1.05"):
        flags["Missing change orders"] = 1

    if not inv.get("delivery_date") and inv.get("requires_shipment"):
        flags["Services not delivered"] = 1

    return flags, sum(flags.values())


# --------------------------------------------------------------------
# Main aggregator
# --------------------------------------------------------------------
def calculate_discrepancy(po_data: Dict[str, Any], inv_data: Dict[str, Any], other_invoices: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    categories = {
        "Quantity Discrepancies": check_quantity_discrepancies(po_data, inv_data),
        "Price Discrepancies": check_price_discrepancies(po_data, inv_data),
        "Tax and Calculation Errors": check_tax_calculation_errors(po_data, inv_data),
        "Duplicate Invoices": check_duplicate_invoices(inv_data, other_invoices or []),
        "Missing / Incomplete Data": check_missing_incomplete_data(inv_data),
        "Unauthorized Charges": check_unauthorized_charges(po_data, inv_data),
        "Line Item Description Mismatches": check_line_item_description_mismatches(po_data, inv_data),
        "Documentation & Reference Errors": check_documentation_reference_errors(po_data, inv_data),
        "Data Entry & Formatting Errors": check_data_entry_formatting_errors(inv_data),
        "Timing Issues": check_timing_issues(inv_data),
        "Calculation Errors": check_calculation_errors(inv_data),
        "Authorization & Approval Errors": check_authorization_approval_errors(po_data, inv_data),
    }

    detailed_flags = {}
    total_score = 0
    for cat, (flags, score) in categories.items():
        total_score += score
        detailed_flags.update(flags)

    return {
        "total_discrepancies": total_score,
        "detailed_flags": detailed_flags,
    }

# Example usage
example_po = {"vendor_name":"Acme","vendor_id":None,"po_number":"10292","invoice_id":"5873","total_amount":13113.28,"subtotal":12647.5,"tax_amount":1250.78,"discount":1100.0,"discount_percent":8.77,"surcharge":0.0,"freight":360.0,"handling":75.0,"cold_chain_surcharge":0.0,"expedited_fee":0.0,"tariff":0.0,"customs":0.0,"service_charge":0.0,"invoice_date":"05/01/2024","po_date":"04/26/2024","delivery_date":"04/30/2024","service_from":"01/01/2024","service_to":"03/31/2024","tax_id":"985652","bank_account":"4605","payment_method":"ACH","payment_terms":"Finance","vendor_approved":True,"grn":"625849","delivery_note":"2914","tracking_number":"AB45638589CA","bill_to":"ABC Cerporation","cost_center":None,"requires_shipment":True,"notes":None,"line_items":[{"description":"Product 1","quantity":30,"total":7500,"unit_price":250},{"description":"Product 2","quantity":5,"total":247.5,"unit_price":49.5},{"description":"Service 1","quantity":1,"total":4800,"unit_price":4800}],"created_by":None}
example_invoice = {"vendor_name":"Acme","vendor_id":None,"po_number":"10292","invoice_id":"5873","total_amount":13113.28,"subtotal":12647.5,"tax_amount":1250.78,"discount":1100.0,"discount_percent":8.77,"surcharge":0.0,"freight":360.0,"handling":75.0,"cold_chain_surcharge":0.0,"expedited_fee":0.0,"tariff":0.0,"customs":0.0,"service_charge":0.0,"invoice_date":"05/01/2024","po_date":"04/26/2024","delivery_date":"04/30/2024","service_from":"01/01/2024","service_to":"03/31/2024","tax_id":"985652","bank_account":"4605","payment_method":"ACH","payment_terms":"Finance","vendor_approved":True,"grn":"625849","delivery_note":"2914","tracking_number":"AB45638589CA","bill_to":"ABC Cerporation","cost_center":None,"requires_shipment":True,"notes":None,"line_items":[{"description":"Product 1","quantity":30,"total":7500,"unit_price":250},{"description":"Product 2","quantity":5,"total":247.5,"unit_price":49.5},{"description":"Service 1","quantity":1,"total":4800,"unit_price":4800}],"created_by":None}
print(calculate_discrepancy(example_po, example_invoice))