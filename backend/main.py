import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db import engine
from models import Base
from auth import (
    fastapi_users,
    UserCreate,
    UserRead,
    UserUpdate,
    auth_backend,
    google_oauth_client,
)
from routes import router as api_router
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

# --- FastAPI Users Routers ---
app.include_router(
    fastapi_users.get_oauth_router(
        google_oauth_client,
        auth_backend,
        state_secret="SUPER_SECRET_OAUTH_STATE",
    ),
    prefix="/auth/google",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth/signup",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

# --- Main API Endpoints ---
app.include_router(api_router)

# --- Database Initialization ---
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
