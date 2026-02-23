from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import analyze, sessions, upload

app = FastAPI(title="form-idable API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Form-Summary"],
)

app.include_router(analyze.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(upload.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
