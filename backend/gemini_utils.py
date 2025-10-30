import httpx
import asyncio
import json
from typing import Dict, Any
from fastapi import HTTPException
import os
import dotenv

dotenv.load_dotenv()

GEMINI_API_URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models/"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

async def call_gemini_api(
    model: str, 
    payload: Dict[str, Any], 
    max_retries: int = 3, 
    base_delay: int = 1
) -> Dict[str, Any]:
    """
    Reusable function to call Gemini API with exponential backoff.
    """
    url = f"{GEMINI_API_URL_BASE}{model}:generateContent?key={GEMINI_API_KEY}"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for attempt in range(max_retries):
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                
                if not result.get("candidates"):
                    raise HTTPException(status_code=500, detail="AI response was empty or malformed.")
                
                part = result["candidates"][0]["content"]["parts"][0]
                if "text" not in part:
                    raise HTTPException(status_code=500, detail="AI response did not contain text.")
                
                return json.loads(part["text"])

            except httpx.RequestError as e:
                print(f"Request failed: {e}. Retrying ({attempt + 1}/{max_retries})...")
                await asyncio.sleep(base_delay * (2 ** attempt))
            except httpx.HTTPStatusError as e:
                print(f"HTTP error: {e}. Retrying ({attempt + 1}/{max_retries})...")
                await asyncio.sleep(base_delay * (2 ** attempt))
            except json.JSONDecodeError as e:
                print(f"Failed to parse AI JSON response: {e}")
                print(f"Raw AI response: {part.get('text', 'NO_TEXT_FOUND')}")
                raise HTTPException(status_code=500, detail="Failed to parse AI JSON response.")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

        raise HTTPException(status_code=504, detail="AI service request timed out after all retries.")

EXTRACTION_MODEL = "gemini-2.5-flash-preview-09-2025"
COMPARISON_MODEL = "gemini-2.5-flash-preview-09-2025"
EXTRACTION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        # Basic identifiers
        "vendor_name": {"type": "STRING", "description": "Name of the vendor or supplier."},
        "vendor_id": {"type": "STRING", "description": "Unique vendor identifier if available."},
        "po_number": {"type": "STRING", "description": "Purchase Order number linked to the invoice."},
        "invoice_id": {"type": "STRING", "description": "Invoice ID or number."},

        # Amounts and totals
        "total_amount": {"type": "NUMBER", "description": "The final total amount due, as a float."},
        "subtotal": {"type": "NUMBER", "description": "Subtotal before tax and discounts."},
        "tax_amount": {"type": "NUMBER", "description": "Tax amount applied to the invoice."},
        "discount": {"type": "NUMBER", "description": "Discount applied to the invoice (absolute value)."},
        "discount_percent": {"type": "NUMBER", "description": "Discount percentage applied, if applicable."},
        "surcharge": {"type": "NUMBER", "description": "Additional surcharge, such as fuel or service fee."},
        "freight": {"type": "NUMBER", "description": "Freight or shipping charges, if applicable."},
        "handling": {"type": "NUMBER", "description": "Handling or processing fee."},
        "cold_chain_surcharge": {"type": "NUMBER", "description": "Refrigeration or cold chain charge."},
        "expedited_fee": {"type": "NUMBER", "description": "Expedited delivery or rush fee."},
        "tariff": {"type": "NUMBER", "description": "Tariffs or import duties applied."},
        "customs": {"type": "NUMBER", "description": "Customs fee if any."},
        "service_charge": {"type": "NUMBER", "description": "Service-related additional charge."},

        # Dates
        "invoice_date": {"type": "STRING", "description": "Date when the invoice was issued (ISO format)."},
        "po_date": {"type": "STRING", "description": "Date when the purchase order was created (ISO format)."},
        "delivery_date": {"type": "STRING", "description": "Date of goods or service delivery (ISO format)."},
        "service_from": {"type": "STRING", "description": "Start date of the service period (ISO format)."},
        "service_to": {"type": "STRING", "description": "End date of the service period (ISO format)."},

        # Vendor & payment details
        "tax_id": {"type": "STRING", "description": "Vendor's GSTIN, VAT, or tax identification number."},
        "bank_account": {"type": "STRING", "description": "Vendor's bank account number or payment reference."},
        "payment_method": {"type": "STRING", "description": "Method of payment (e.g., ACH, Wire, Card)."},
        "payment_terms": {"type": "STRING", "description": "Payment terms like Net30, Net45, etc."},
        "vendor_approved": {"type": "BOOLEAN", "description": "Whether the vendor is approved or in vendor master."},

        # Logistics / Reference
        "grn": {"type": "STRING", "description": "Goods Received Note or delivery receipt reference."},
        "delivery_note": {"type": "STRING", "description": "Delivery note or shipment identifier."},
        "tracking_number": {"type": "STRING", "description": "Shipment or logistics tracking number."},
        "bill_to": {"type": "STRING", "description": "Billing address or legal entity billed."},
        "cost_center": {"type": "STRING", "description": "Cost center or department responsible for the order."},
        "requires_shipment": {"type": "BOOLEAN", "description": "Whether the order requires shipment tracking."},

        # Descriptive or textual fields
        "notes": {"type": "STRING", "description": "Additional notes, comments, or remarks."},

        "is_invoice": {"type": "BOOLEAN", "description": "Indicates if the document is an invoice."},

        # Line-level details
        "line_items": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "description": {"type": "STRING", "description": "Description of the product or service."},
                    "quantity": {"type": "NUMBER", "description": "Quantity billed or ordered."},
                    "unit_price": {"type": "NUMBER", "description": "Price per unit item."},
                    "total": {"type": "NUMBER", "description": "Line total = quantity × unit price."},
                    "part_number": {"type": "STRING", "description": "Product or part identifier."},
                    "brand": {"type": "STRING", "description": "Brand name if specified."},
                    "color": {"type": "STRING", "description": "Color specification if applicable."},
                    "size": {"type": "STRING", "description": "Size or dimension if applicable."},
                    "spec": {"type": "STRING", "description": "Technical specification or model info."},
                    "tax_exempt": {"type": "BOOLEAN", "description": "Whether the item is tax-exempt."}
                },
                "required": ["description", "quantity", "total"]
            }
        }
    },
    "required": ["vendor_name", "total_amount", "line_items"]
}


COMPARISON_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "status": {"type": "STRING", "enum": ["Matched", "Mismatched", "Error"]},
        "discrepancies": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "field": {"type": "STRING", "description": "The name of the field with a discrepancy."},
                    "po_value": {"type": "STRING", "description": "The value from the Purchase Order."},
                    "invoice_value": {"type": "STRING", "description": "The value from the Invoice."},
                    "comment": {"type": "STRING", "description": "A brief comment on the discrepancy."}
                },
                "required": ["field", "po_value", "invoice_value", "comment"]
            }
        },
        "summary": {"type": "STRING", "description": "A concise, human-readable summary of the comparison."}
    },
    "required": ["status", "discrepancies", "summary"]
}