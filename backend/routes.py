from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,text
from db import get_async_session
from datetime import datetime
from vps_utils import compute_vps_from_compare_data
from models import InvoiceDB, PurchaseOrderDB, CompareResponseDB, GmailUser, ReportDB
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


# --- Helper function for optional authentication ---
async def get_optional_user(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_async_session)
) -> Optional[dict]:
    """
    Optional authentication dependency.
    Returns user info if valid token is provided, None otherwise.
    Does not raise exceptions - allows unauthenticated access.
    """
    if not authorization:
        return None
    
    try:
        # Import here to avoid circular dependency
        from mail import verify_token
        
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None
        
        payload = verify_token(token)
        user_email = payload.get("email")
        
        if not user_email:
            return None
        
        # Verify user exists in database
        res_user = await session.execute(select(GmailUser).where(GmailUser.email == user_email))
        user = res_user.scalar_one_or_none()
        
        if not user:
            return None
        
        # Check if token was invalidated by logout
        if user.logged_out_at and user.logged_out_at > payload.get("iat", 0):
            return None
        
        return {
            "id": user.id,
            "email": user.email,
            "user_info": user.user_info,
        }
    except Exception as e:
        # Log error but don't raise - allow unauthenticated access
        print(f"Optional auth failed: {e}")
        return None


# --- Pydantic Schemas ---
class DocumentData(BaseModel):
    """Schema for the extracted data from a document."""
    id: Optional[int] = None
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
    vendor_id: Optional[str] = Field(None, description="Vendor identifier associated with the documents.")
    discrepancy: List[Discrepancy] = Field(default_factory=list)
    summary: str = Field(..., description="A human-readable summary of the findings.")


# --- ROUTES ---
@router.post("/extract-data", response_model=ExtractResponse)
async def extract_data(
    request: ExtractRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: Optional[dict] = Depends(get_optional_user),
):
    """
    Receives a base64-encoded image and uses Gemini Vision to extract
    structured data according to EXTRACTION_SCHEMA.
    
    If user is authenticated, the document will be linked to their account.
    If not authenticated, the document is created without a user link.
    """
    print(f"Received extraction request for: {request.image_mime_type}")

    extraction_prompt = (
        "You are an expert OCR and data extraction service. "
        "Analyze the provided document image (invoice or PO) and extract key information "
        "according to the provided JSON schema. "
        "If a field is not present, omit it from the JSON."
        "Provide is_invoice as true for invoices, false for purchase orders."
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
        
        # Get user ID if authenticated, None otherwise
        user_id = current_user["id"] if current_user else None
        if current_user:
            print(f"Document created by authenticated user: {current_user['email']} (ID: {user_id})")
        else:
            print("Document created without authentication")

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
            created_by=user_id,  # Set to user's ID if authenticated, None otherwise
        )

        session.add(db_doc)
        await session.commit()
        return {**validated_data.model_dump(), "id": db_doc.id}

    except Exception as e:
        print(f"Extraction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Data extraction failed: {str(e)}")


@router.post("/compare-data", response_model=CompareResponse)
async def compare_data(request: CompareRequest, session: AsyncSession = Depends(get_async_session)):
    """
    Compare a Purchase Order and Invoice by fetching them from DB using their IDs.
    Performs rule-based discrepancy detection and Gemini reasoning to produce a structured report.
    Also creates a corresponding report record (chat-style) with full context.
    """
    print(f"Received comparison request: PO_ID={request.po_id}, INVOICE_ID={request.invoice_id}")

    from discrepancy_utils import calculate_discrepancy
    from models import PurchaseOrderDB, InvoiceDB, CompareResponseDB, ReportDB

    # ---------------------- Step 1: Fetch PO & Invoice ----------------------
    po_record = await session.get(PurchaseOrderDB, request.po_id)
    invoice_record = await session.get(InvoiceDB, request.invoice_id)

    if not po_record:
        raise HTTPException(status_code=404, detail=f"Purchase Order with ID {request.po_id} not found.")
    if not invoice_record:
        raise HTTPException(status_code=404, detail=f"Invoice with ID {request.invoice_id} not found.")

    # ---------------------- Step 2: Convert models to dict ----------------------
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

    # ---------------------- Step 3: Discrepancy detection ----------------------
    discrepancy_result = calculate_discrepancy(po_data, invoice_data)
    discrepancy_vector = list(discrepancy_result["detailed_flags"].values())
    print(f"Discrepancy vector generated: {discrepancy_vector}")

    # ---------------------- Step 4: Prepare Gemini reasoning prompt ----------------------
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
      "summary": "Short narrative summarizing key discrepancies between PO and Invoice.",
      "discrepancy": [
        {{
          "name": "Calculation error",
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

    payload = {
        "contents": [{"parts": [{"text": comparison_prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2
        }
    }

    # ---------------------- Step 5: Call Gemini ----------------------
    try:
        comparison_json = await call_gemini_api(COMPARISON_MODEL, payload)
        comparison_json["vendor_id"] = invoice_record.vendor_id or po_record.vendor_id
        validated_report = CompareResponse(**comparison_json)

        # ---------------------- Step 6: Store CompareResult ----------------------
        db_cmp = CompareResponseDB(
            vendor_id=validated_report.vendor_id,
            discrepancy=[i.model_dump() for i in validated_report.discrepancy],
            discrepancy_vector=discrepancy_vector,
            summary=validated_report.summary,
            invoice_id=invoice_record.id,
            po_id=po_record.id,
            created_by=invoice_record.created_by,
        )
        session.add(db_cmp)
        await session.commit()

        # ---------------------- Step 7: Create report (summary + full data) ----------------------
        initial_messages = [
            {
                "role": "server",
                "content": (
                    f"**Summary:** {validated_report.summary}\n\n"
                    f"**Purchase Order Data:**\n```json\n{json.dumps(po_data, indent=2)}\n```\n\n"
                    f"**Invoice Data:**\n```json\n{json.dumps(invoice_data, indent=2)}\n```"
                ),
            }
        ]

        new_report = ReportDB(
            messages=initial_messages,
            created_by=invoice_record.created_by,
        )

        session.add(new_report)
        await session.commit()

        return {
            **validated_report.model_dump(),
            "report_id": new_report.id
        }

    except Exception as e:
        print(f"Comparison failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Data comparison failed: {str(e)}")


@router.get("/eda-summary/{user_id}")
async def eda_summary(user_id: int, session: AsyncSession = Depends(get_async_session)):
    from eda_utils import get_user_eda
    eda_data = await get_user_eda(session, user_id)
    return eda_data

class VPSRequest(BaseModel):
    comparison_id: int = Field(..., description="ID of comparison record in 'comparisons' table")


class VPSResponse(BaseModel):
    vendor_id: str
    persona: str
    vps_score: float
    aggregated_risk: float
    last_updated: datetime

DEFAULT_PERSONA = "margin"

@router.post("/calculate", response_model=VPSResponse)
async def calculate_vendor_vps(
    data: VPSRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Calculates and stores Vendor Persona Score (VPS) for a vendor using a comparison record.
    Persona is automatically set to 'compliance'.
    Applies time-decay when updating the vendor's historical score.
    """
    # 1️⃣ Fetch comparison record
    comparison = await session.get(CompareResponseDB, data.comparison_id)
    if not comparison:
        raise HTTPException(status_code=404, detail=f"Comparison ID {data.comparison_id} not found.")
    if not comparison.vendor_id:
        raise HTTPException(status_code=400, detail="Comparison record missing vendor_id.")
    if not comparison.discrepancy or not isinstance(comparison.discrepancy, list):
        raise HTTPException(status_code=400, detail="Invalid discrepancy format in comparison record.")

    # 2️⃣ Convert discrepancy data to 82-length binary vector
    discrepancy_vector = comparison.discrepancy_vector
    # Validate
    # 3️⃣ Compute VPS and update DB
    vps_score = await compute_vps_from_compare_data(
        session,
        {
            "vendor_id": comparison.vendor_id,
            "discrepancies": discrepancy_vector,
        },
        persona=DEFAULT_PERSONA
    )

    # 4️⃣ Fetch latest stored VPS record
    result = await session.execute(
        text("""
            SELECT vendor_id, persona, vps_score, aggregated_risk, last_updated
            FROM vendor_vps
            WHERE vendor_id = :vendor_id AND persona = :persona
            ORDER BY last_updated DESC
            LIMIT 1
        """),
        {"vendor_id": comparison.vendor_id, "persona": "margin"}  # since persona is fixed
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=500, detail="VPS calculation failed to store.")

    return VPSResponse(
        vendor_id=row.vendor_id,
        persona=row.persona,
        vps_score=row.vps_score,
        aggregated_risk=row.aggregated_risk,
        last_updated=row.last_updated,
    )

@router.get("/")
def read_root():
    return {"message": "AI Document Reconciliation API is running."}


# --------------------------- REPORTS ROUTES ---------------------------
@router.get("/reports")
async def list_reports(
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(select(ReportDB))
    reports = result.scalars().all()
    return [
        {
            "id": r.id,
            "messages": r.messages,
            "created_by": r.created_by,
            "created_at": r.created_at,
        }
        for r in reports
    ]


@router.get("/reports/{report_id}")
async def get_report(
    report_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    report = await session.get(ReportDB, report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found.")
    return {
        "id": report.id,
        "messages": report.messages,
        "created_by": report.created_by,
        "created_at": report.created_at,
    }

class MessageRequest(BaseModel):
    role: str = Field(..., description="Message sender role: 'user' or 'server'")
    content: str = Field(..., description="The message content text")

class MessageResponse(BaseModel):
    reply: str = Field(..., description="Gemini's response text")


@router.post("/message/{report_id}", response_model=MessageResponse)
async def continue_report_chat(
    report_id: int,
    message: MessageRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Continues the conversation for a given report using Gemini API.
    The full message history is used as context.
    """
    # 1️⃣ Fetch report
    report = await session.get(ReportDB, report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    # 2️⃣ Append new message from user
    report.messages.append({"role": message.role, "content": message.content})
    await session.commit()

    # 3️⃣ Prepare chat-style Gemini prompt
    context_messages = "\n".join(
        [f"{m['role'].upper()}: {m['content']}" for m in report.messages]
    )

    prompt = f"""
    You are an intelligent financial audit assistant continuing a report discussion.

    Below is the full conversation so far between the system and the user.
    Use context to generate a concise, accurate, professional reply.

    Conversation:
    {context_messages}

    Respond in natural, human-like language (no JSON unless requested).
    """

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 400,
        },
    }

    # 4️⃣ Send to Gemini
    try:
        gemini_reply = await call_gemini_api(COMPARISON_MODEL, payload)
        reply_text = gemini_reply.get("text") or str(gemini_reply)

        # 5️⃣ Append Gemini’s reply as a new server message
        report.messages.append({"role": "server", "content": reply_text})
        await session.commit()

        return {"reply": reply_text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini message failed: {str(e)}")
