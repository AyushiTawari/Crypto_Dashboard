from fastapi import FastAPI
from app.routers import snapshots

app = FastAPI(title="Crypto Dashboard API")
app.include_router(snapshots.router)