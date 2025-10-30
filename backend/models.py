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
    DateTime,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from fastapi_users.db import SQLAlchemyBaseUserTable
from datetime import datetime

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


# --------------------------- GMAIL INTEGRATION TABLES -----------------------
class GmailUser(Base):
    __tablename__ = "gmail_users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    user_info = Column(JSONB, nullable=True)
    credentials = Column(JSONB, nullable=True)
    watch_expiration = Column(DateTime, nullable=True)
    history_id = Column(String, nullable=True)
    last_login = Column(DateTime, nullable=True)
    last_sync = Column(DateTime(timezone=True), nullable=True)
    logged_out_at = Column(DateTime, nullable=True)


class GmailEmail(Base):
    __tablename__ = "gmail_emails"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True, nullable=False)
    message_id = Column(String, unique=True, index=True, nullable=False)
    thread_id = Column(String, nullable=True)
    from_addr = Column(String, nullable=True)
    to_addr = Column(String, nullable=True)
    subject = Column(String, nullable=True)
    date = Column(String, nullable=True)
    snippet = Column(Text, nullable=True)
    labels = Column(JSONB, nullable=False, default=list)
    internal_date = Column(String, index=True, nullable=True)
    received_at = Column(DateTime, default=datetime.utcnow)

    body_plain = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)
    body_snippet = Column(Text, nullable=True)

    has_attachments = Column(Boolean, default=False)
    attachments = Column(JSONB, nullable=False, default=list)

    priority = Column(String, nullable=True)
    is_important = Column(Boolean, default=False)
    category = Column(String, nullable=True)
    sender_domain = Column(String, index=True, nullable=True)


class GmailSenderStat(Base):
    __tablename__ = "gmail_sender_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True, nullable=False)
    domain = Column(String, index=True, nullable=False)
    email_count = Column(Integer, default=0)
    last_email_date = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_email", "domain", name="uq_user_domain"),
    )


class OAuthState(Base):
    __tablename__ = "oauth_states"

    id = Column(Integer, primary_key=True, index=True)
    state = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)


class EmailEvent(Base):
    __tablename__ = "email_events"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True, nullable=False)
    event_type = Column(String, nullable=False)
    message_id = Column(String, index=True, nullable=True)
    sender = Column(String, nullable=True)
    subject = Column(String, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)