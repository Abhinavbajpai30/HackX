import math
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import CompareResponseDB, DocumentDataDB, Base
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

# ---------------------- CONFIG ----------------------
LAMBDA_DECAY = 0.05   # Time decay rate
KAPPA_SENSITIVITY = 0.1  # Score sensitivity
DEFAULT_PERSONA = "margin"  # default persona if none specified

# Example persona-based severity weightings for 82 fields
# (In production, load from DB or config)
PERSONA_SEVERITY_WEIGHTS = {
    "compliance": [2.0 if i in range(10, 20) else 1.0 for i in range(82)],
    "margin": [2.0 if i in range(0, 10) else 1.0 for i in range(82)],
    "operations": [2.0 if i in range(20, 30) else 1.0 for i in range(82)],
}

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

    Args:
        session: Async SQLAlchemy session.
        vendor_id: Vendor identifier.
        persona: Persona type ('compliance', 'margin', 'operations', etc.)
        discrepancy_vector: List of 82 integers (0 or 1).
        timestamp: Optional; defaults to current UTC time.

    Returns:
        Computed VPS score (float between 0 and 100).
    """
    timestamp = timestamp or datetime.utcnow()
    weights = PERSONA_SEVERITY_WEIGHTS.get(persona, PERSONA_SEVERITY_WEIGHTS[DEFAULT_PERSONA])

    # Step 1: Compute Φ(v, T)
    # Since we only have a single snapshot of discrepancies (0 or 1),
    # we assume these represent occurrences at time T
    phi_vector = [val * math.exp(-LAMBDA_DECAY * 0) for val in discrepancy_vector]

    # Step 2: Compute R(v, T, p)
    aggregated_risk = sum(w * phi for w, phi in zip(weights, phi_vector))

    # Step 3: Normalize to VPS
    vps_score = 100 * math.exp(-KAPPA_SENSITIVITY * aggregated_risk)

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
        updated_vps = (decayed_score + new_vps) / 2  # simple moving average with decay
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
      - discrepancies (list of 82 binary values)
    """
    vendor_id = compare_data.get("vendor_id")
    discrepancy_vector = compare_data.get("discrepancies")

    if not vendor_id or not discrepancy_vector or len(discrepancy_vector) != 82:
        raise ValueError("Invalid compare-data input: must include vendor_id and 82-length discrepancy vector.")

    return await calculate_vps(session, vendor_id, persona, discrepancy_vector)
