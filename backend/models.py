from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Text,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from fastapi_users.db import SQLAlchemyBaseUserTable

Base = declarative_base()


class UserTable(SQLAlchemyBaseUserTable[int], Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)

# ---------------------- ABSTRACT BASE MODEL -------------------------
class DocumentDataDB:
    """Abstract mixin for shared document fields."""

    id = Column(Integer, primary_key=True, index=True)

    # Core identifiers
    vendor_name = Column(String, nullable=True)
    vendor_id = Column(String, nullable=True)
    po_number = Column(String, index=True, nullable=True)
    invoice_id = Column(String, index=True, nullable=True)

    # Financials
    total_amount = Column(Float, nullable=True)
    subtotal = Column(Float, nullable=True)
    tax_amount = Column(Float, nullable=True)
    discount = Column(Float, nullable=True)
    discount_percent = Column(Float, nullable=True)
    surcharge = Column(Float, nullable=True)
    freight = Column(Float, nullable=True)
    handling = Column(Float, nullable=True)
    cold_chain_surcharge = Column(Float, nullable=True)
    expedited_fee = Column(Float, nullable=True)
    tariff = Column(Float, nullable=True)
    customs = Column(Float, nullable=True)
    service_charge = Column(Float, nullable=True)

    # Dates
    invoice_date = Column(String, nullable=True)
    po_date = Column(String, nullable=True)
    delivery_date = Column(String, nullable=True)
    service_from = Column(String, nullable=True)
    service_to = Column(String, nullable=True)

    # Vendor & Payment
    tax_id = Column(String, nullable=True)
    bank_account = Column(String, nullable=True)
    payment_method = Column(String, nullable=True)
    payment_terms = Column(String, nullable=True)
    vendor_approved = Column(Boolean, nullable=True)

    # Logistics & References
    grn = Column(String, nullable=True)
    delivery_note = Column(String, nullable=True)
    tracking_number = Column(String, nullable=True)
    bill_to = Column(String, nullable=True)
    cost_center = Column(String, nullable=True)
    requires_shipment = Column(Boolean, nullable=True)

    # Notes and metadata
    notes = Column(String, nullable=True)
    line_items = Column(JSONB, nullable=False, default=list)

    is_invoice = Column(Boolean, nullable=False, default=False)

    created_by = Column(Integer, ForeignKey("user.id"), nullable=True)

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    __abstract__ = True


# ----------------------- PURCHASE ORDER TABLE -----------------------
class PurchaseOrderDB(DocumentDataDB, Base):
    __tablename__ = "purchase_orders"

    po_number = Column(String, unique=True, index=True, nullable=False)

    related_invoices = relationship(
        "InvoiceDB",
        back_populates="related_po",
        cascade="all, delete-orphan",
    )


# --------------------------- INVOICE TABLE --------------------------
class InvoiceDB(DocumentDataDB, Base):
    __tablename__ = "invoices"

    invoice_id = Column(String, unique=True, index=True, nullable=False)
    po_number = Column(String, ForeignKey("purchase_orders.po_number"), nullable=True)

    related_po = relationship(
        "PurchaseOrderDB",
        back_populates="related_invoices",
        foreign_keys=[po_number],
    )


# --------------------------- COMPARISON TABLE -----------------------
class CompareResponseDB(Base):
    __tablename__ = "comparisons"

    id = Column(Integer, primary_key=True, index=True)
    discrepancy = Column(JSONB, nullable=False, default=list)  # stores list[dict]
    summary = Column(Text, nullable=False)

    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("user.id"), nullable=True)