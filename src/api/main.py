from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import query, sessions

app = FastAPI(
    title="Ad-Hoc Data Visualization Tool",
    description="Upload CSV → ask questions → get intelligent charts + insights.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router, prefix="/api/v1")
app.include_router(query.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}
