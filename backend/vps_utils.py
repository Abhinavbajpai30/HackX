import math
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from models import Base

# ---------------------- CONFIG ----------------------
LAMBDA_DECAY = 0.05          # Time decay rate
KAPPA_SENSITIVITY = 0.1      # Score sensitivity
DEFAULT_PERSONA = "margin"    # default persona if none specified
MAX_FIELDS = 82               # expected vector length

# Example persona-based severity weightings for 82 fields
PERSONA_SEVERITY_WEIGHTS = {
    "compliance": [2.0 if i in range(10, 20) else 1.0 for i in range(MAX_FIELDS)],
    "margin": [2.0 if i in range(0, 10) else 1.0 for i in range(MAX_FIELDS)],
    "operations": [2.0 if i in range(20, 30) else 1.0 for i in range(MAX_FIELDS)],
}

# ---------------------- MODEL ----------------------
class VendorVPSDB(Base):
    __tablename__ = "vendor_vps"

    __table_args__ = {"extend_existing": True}  # ✅ fix duplicate definition

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(String, index=True, nullable=False)
    persona = Column(String, nullable=False)
    vps_score = Column(Float, nullable=False)
    aggregated_risk = Column(Float, nullable=False)
    last_updated = Column(DateTime, nullable=False)
    decay_weight = Column(Float, nullable=True)
    history = Column(JSON, default=list)


# ---------------------- VPS CALCULATION ----------------------
async def calculate_vps(
    session: AsyncSession,
    vendor_id: str,
    persona: str,
    discrepancy_vector: list[int],
    timestamp: datetime = None,
) -> float:
    """
    Calculates Vendor Persona Score (VPS) for a vendor given discrepancy vector (0/1 values).
    Handles cases where discrepancy_vector != 82.
    """
    timestamp = timestamp or datetime.utcnow()
    weights = PERSONA_SEVERITY_WEIGHTS.get(persona, PERSONA_SEVERITY_WEIGHTS[DEFAULT_PERSONA])

    # Ensure discrepancy vector length = MAX_FIELDS
    n = len(discrepancy_vector)
    if n < MAX_FIELDS:
        discrepancy_vector = discrepancy_vector + [0] * (MAX_FIELDS - n)
    elif n > MAX_FIELDS:
        discrepancy_vector = discrepancy_vector[:MAX_FIELDS]

    # Align weights length
    weights = weights[:len(discrepancy_vector)]

    # Step 1: Compute Φ(v, T)
    phi_vector = [val * math.exp(-LAMBDA_DECAY * 0) for val in discrepancy_vector]

    # Step 2: Compute aggregated risk
    aggregated_risk = sum(w * phi for w, phi in zip(weights, phi_vector))

    # Step 3: Normalize to VPS (exponential decay of risk)
    vps_score = 100 * math.exp(-KAPPA_SENSITIVITY * aggregated_risk)
    vps_score = round(vps_score, 2)

    # Step 4: Store / update in DB
    await update_vendor_vps(session, vendor_id, persona, vps_score, aggregated_risk, timestamp)
    return vps_score


# ---------------------- DECAY + UPDATE ----------------------
async def update_vendor_vps(
    session: AsyncSession,
    vendor_id: str,
    persona: str,
    new_vps: float,
    new_risk: float,
    timestamp: datetime,
):
    """
    Updates or inserts a vendor's VPS with time decay applied.
    """
    query = await session.execute(
        select(VendorVPSDB).where(
            VendorVPSDB.vendor_id == vendor_id,
            VendorVPSDB.persona == persona
        )
    )
    existing = query.scalar_one_or_none()

    if existing:
        # Apply time decay to prior score
        delta_days = (timestamp - existing.last_updated).days or 1
        decay_factor = math.exp(-LAMBDA_DECAY * delta_days)

        decayed_score = existing.vps_score * decay_factor
        updated_vps = (decayed_score + new_vps) / 2  # weighted moving avg
        updated_risk = (existing.aggregated_risk * decay_factor + new_risk) / 2

        existing.vps_score = round(updated_vps, 2)
        existing.aggregated_risk = round(updated_risk, 4)
        existing.last_updated = timestamp
        existing.decay_weight = decay_factor
        existing.history.append({
            "timestamp": timestamp.isoformat(),
            "vps": new_vps,
            "risk": new_risk
        })

    else:
        existing = VendorVPSDB(
            vendor_id=vendor_id,
            persona=persona,
            vps_score=round(new_vps, 2),
            aggregated_risk=round(new_risk, 4),
            last_updated=timestamp,
            history=[{"timestamp": timestamp.isoformat(), "vps": new_vps, "risk": new_risk}],
        )
        session.add(existing)

    await session.commit()


# ---------------------- ENTRYPOINT WRAPPER ----------------------
async def compute_vps_from_compare_data(session: AsyncSession, compare_data: dict, persona: str = DEFAULT_PERSONA):
    """
    Computes and stores VPS given a /compare-data response.
    Expects compare_data to contain:
      - vendor_id (str)
      - discrepancies (list[int]) — can be shorter/longer than 82
    """
    vendor_id = compare_data.get("vendor_id")
    discrepancy_vector = compare_data.get("discrepancies")

    if not vendor_id or not discrepancy_vector or not isinstance(discrepancy_vector, list):
        raise ValueError("Invalid compare-data input: must include vendor_id and discrepancy vector list.")

    return await calculate_vps(session, vendor_id, persona, discrepancy_vector)
