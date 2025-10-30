import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db import engine
from models import Base
from routes import router as api_router
from mail import app as mail_app
import os

app = FastAPI(
    title="AI Document Reconciliation API",
    description="Extracts and compares data from invoices and POs using AI.",
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ✅ Allow all for now (lock down in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Main API Endpoints ---
app.include_router(api_router)
app.include_router(mail_app.router)

# --- Database Initialization ---
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
