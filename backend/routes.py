from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_async_session
from models import InvoiceDB, PurchaseOrderDB, CompareResponseDB
from auth import fastapi_users, UserRead
from typing import List, Optional, Dict, Any
from gemini_utils import (
    call_gemini_api,
    EXTRACTION_SCHEMA,
    EXTRACTION_MODEL,
    COMPARISON_MODEL,
    COMPARISON_SCHEMA,
)
import json

router = APIRouter()


# --- Pydantic Schemas ---
class DocumentData(BaseModel):
    """Schema for the extracted data from a document."""

    # Core identifiers
    vendor_name: Optional[str] = None
    vendor_id: Optional[str] = None
    po_number: Optional[str] = None
    invoice_id: Optional[str] = None

    is_invoice: bool = Field(..., description="True if the document is an invoice, else False.")

    # Financials
    total_amount: Optional[float] = None
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    discount: Optional[float] = None
    discount_percent: Optional[float] = None
    surcharge: Optional[float] = None
    freight: Optional[float] = None
    handling: Optional[float] = None
    cold_chain_surcharge: Optional[float] = None
    expedited_fee: Optional[float] = None
    tariff: Optional[float] = None
    customs: Optional[float] = None
    service_charge: Optional[float] = None

    # Dates
    invoice_date: Optional[str] = None
    po_date: Optional[str] = None
    delivery_date: Optional[str] = None
    service_from: Optional[str] = None
    service_to: Optional[str] = None

    # Vendor & Payment
    tax_id: Optional[str] = None
    bank_account: Optional[str] = None
    payment_method: Optional[str] = None
    payment_terms: Optional[str] = None
    vendor_approved: Optional[bool] = None

    # Logistics & References
    grn: Optional[str] = None
    delivery_note: Optional[str] = None
    tracking_number: Optional[str] = None
    bill_to: Optional[str] = None
    cost_center: Optional[str] = None
    requires_shipment: Optional[bool] = None

    # Notes and metadata
    notes: Optional[str] = None
    line_items: List[Dict[str, Any]] = Field(default_factory=list)

    # Relationships
    created_by: Optional[int] = None

class ExtractRequest(BaseModel):
    """Request model for the /extract-data endpoint."""
    image_data: str = Field(..., description="Base64-encoded image string.")
    image_mime_type: str = Field(..., description="MIME type of the image (e.g., 'image/png').")


class ExtractResponse(DocumentData):
    """Schema for the extracted data from a document."""
    pass


class CompareRequest(BaseModel):
    """Request model for the /compare-data endpoint."""
    po_id: int
    invoice_id: int


class Discrepancy(BaseModel):
    """Schema for a single discrepancy."""
    name: str = Field(..., description="Name of the discrepancy.")
    details: str = Field(..., description="Detailed explanation of the discrepancy.")


class CompareResponse(BaseModel):
    """Schema for the final comparison report."""
    discrepancy: List[Discrepancy] = Field(default_factory=list)
    summary: str = Field(..., description="A human-readable summary of the findings.")


# --- ROUTES ---
@router.post("/extract-data", response_model=ExtractResponse)
async def extract_data(
    request: ExtractRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Receives a base64-encoded image and uses Gemini Vision to extract
    structured data according to EXTRACTION_SCHEMA.
    """
    print(f"Received extraction request for: {request.image_mime_type}")

    extraction_prompt = (
        "You are an expert OCR and data extraction service. "
        "Analyze the provided document image (invoice or PO) and extract key information "
        "according to the provided JSON schema. "
        "If a field is not present, omit it from the JSON."
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": extraction_prompt},
                    {
                        "inlineData": {
                            "mimeType": request.image_mime_type,
                            "data": request.image_data,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": EXTRACTION_SCHEMA,
        },
    }

    try:
        extracted_json = await call_gemini_api(EXTRACTION_MODEL, payload)
        validated_data = DocumentData(**extracted_json)

        ModelClass = InvoiceDB if validated_data.is_invoice else PurchaseOrderDB

        db_doc = ModelClass(
            # Core identifiers
            vendor_name=validated_data.vendor_name,
            vendor_id=validated_data.vendor_id,
            po_number=validated_data.po_number,
            invoice_id=getattr(validated_data, "invoice_id", None),

            is_invoice=validated_data.is_invoice,
            # Financials
            total_amount=validated_data.total_amount,
            subtotal=validated_data.subtotal,
            tax_amount=validated_data.tax_amount,
            discount=validated_data.discount,
            discount_percent=validated_data.discount_percent,
            surcharge=validated_data.surcharge,
            freight=validated_data.freight,
            handling=validated_data.handling,
            cold_chain_surcharge=validated_data.cold_chain_surcharge,
            expedited_fee=validated_data.expedited_fee,
            tariff=validated_data.tariff,
            customs=validated_data.customs,
            service_charge=validated_data.service_charge,

            # Dates
            invoice_date=validated_data.invoice_date,
            po_date=validated_data.po_date,
            delivery_date=validated_data.delivery_date,
            service_from=validated_data.service_from,
            service_to=validated_data.service_to,

            # Vendor & Payment
            tax_id=validated_data.tax_id,
            bank_account=validated_data.bank_account,
            payment_method=validated_data.payment_method,
            payment_terms=validated_data.payment_terms,
            vendor_approved=validated_data.vendor_approved,

            # Logistics & References
            grn=validated_data.grn,
            delivery_note=validated_data.delivery_note,
            tracking_number=validated_data.tracking_number,
            bill_to=validated_data.bill_to,
            cost_center=validated_data.cost_center,
            requires_shipment=validated_data.requires_shipment,

            # Notes and metadata
            notes=validated_data.notes,
            line_items=validated_data.line_items,

            # Relationships
            created_by=getattr(validated_data, "created_by", None),
        )

        session.add(db_doc)
        await session.commit()
        return validated_data

    except Exception as e:
        print(f"Extraction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Data extraction failed: {str(e)}")


@router.post("/compare-data", response_model=CompareResponse)
async def compare_data(request: CompareRequest, session: AsyncSession = Depends(get_async_session)):
    """
    Compare a Purchase Order and Invoice by fetching from DB using IDs.
    Runs rule-based discrepancy detection and Gemini reasoning to produce a structured report.
    """
    print(f"Received comparison request: PO_ID={request.po_id}, INVOICE_ID={request.invoice_id}")

    from models import PurchaseOrderDB, InvoiceDB, CompareResponseDB
    from discrepancy_utils import calculate_discrepancy

    # Step 1: Fetch PO and Invoice
    po_record = await session.get(PurchaseOrderDB, request.po_id)
    invoice_record = await session.get(InvoiceDB, request.invoice_id)

    if not po_record:
        raise HTTPException(status_code=404, detail=f"Purchase Order with ID {request.po_id} not found.")
    if not invoice_record:
        raise HTTPException(status_code=404, detail=f"Invoice with ID {request.invoice_id} not found.")

    # Step 2: Convert SQLAlchemy objects to full dicts (all fields)
    def model_to_dict(obj):
        return {
            "id": obj.id,
            "vendor_name": obj.vendor_name,
            "vendor_id": obj.vendor_id,
            "po_number": obj.po_number,
            "invoice_id": obj.invoice_id,
            "total_amount": obj.total_amount,
            "subtotal": obj.subtotal,
            "tax_amount": obj.tax_amount,
            "discount": obj.discount,
            "discount_percent": obj.discount_percent,
            "surcharge": obj.surcharge,
            "freight": obj.freight,
            "handling": obj.handling,
            "cold_chain_surcharge": obj.cold_chain_surcharge,
            "expedited_fee": obj.expedited_fee,
            "tariff": obj.tariff,
            "customs": obj.customs,
            "service_charge": obj.service_charge,
            "invoice_date": obj.invoice_date,
            "po_date": obj.po_date,
            "delivery_date": obj.delivery_date,
            "service_from": obj.service_from,
            "service_to": obj.service_to,
            "tax_id": obj.tax_id,
            "bank_account": obj.bank_account,
            "payment_method": obj.payment_method,
            "payment_terms": obj.payment_terms,
            "vendor_approved": obj.vendor_approved,
            "grn": obj.grn,
            "delivery_note": obj.delivery_note,
            "tracking_number": obj.tracking_number,
            "bill_to": obj.bill_to,
            "cost_center": obj.cost_center,
            "requires_shipment": obj.requires_shipment,
            "notes": obj.notes,
            "line_items": obj.line_items,
            "created_by": obj.created_by,
        }

    po_data = model_to_dict(po_record)
    invoice_data = model_to_dict(invoice_record)

    # Step 3: Rule-based discrepancy detection
    discrepancy_result = calculate_discrepancy(po_data, invoice_data)

    # Step 4: Build Gemini reasoning prompt
    comparison_prompt = f"""
    You are an expert financial document auditor. You are given:

    1️⃣ A **Purchase Order (PO)** in JSON format.
    2️⃣ An **Invoice** in JSON format.
    3️⃣ A **discrepancy analysis output** generated by an automated rule-based system.

    Your task:
    - Interpret the discrepancy output dictionary.
    - Identify all discrepancies where the flag = 1.
    - For each active discrepancy, explain *where and how* it occurs using the PO and Invoice data.
    - Summarize all findings clearly.
    - Return strictly valid JSON in the following structure:

    {{
      "summary": "Short narrative summarizing all key discrepancies between PO and Invoice.",
      "discrepancy": [
        {{
          "name": "Calculation errors",
          "details": "Invoice total (13113.28) does not match subtotal + tax - discount (12798.28)."
        }}
      ]
    }}

    ### Purchase Order:
    {json.dumps(po_data, indent=2)}

    ### Invoice:
    {json.dumps(invoice_data, indent=2)}

    ### Discrepancy Output:
    {json.dumps(discrepancy_result, indent=2)}
    """

    # Step 5: Call Gemini API
    payload = {
        "contents": [{"parts": [{"text": comparison_prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2
        }
    }

    try:
        comparison_json = await call_gemini_api(COMPARISON_MODEL, payload)
        print(comparison_json)
        validated_report = CompareResponse(**comparison_json)

        # Step 6: Store the comparison result
        db_cmp = CompareResponseDB(
            discrepancy=[i.model_dump() for i in validated_report.discrepancy],
            summary=validated_report.summary,
            invoice_id=invoice_record.id,
            created_by=invoice_record.created_by,
        )
        session.add(db_cmp)
        await session.commit()

        return validated_report

    except Exception as e:
        print(f"Comparison failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Data comparison failed: {str(e)}")



@router.get("/")
def read_root():
    return {"message": "AI Document Reconciliation API is running."}
