from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .bank_api import router as bank_router

app = FastAPI(title="Hisab Kitab API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(bank_router)


@app.get("/health")
def health():
    return {"status": "ok"}
