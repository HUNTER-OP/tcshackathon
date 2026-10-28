import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import bank_api, llm, metrics
from .bank_api import router as bank_router
from .pipeline import ChatResult, handle_message
from .seed import seed

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Hisab Kitab API", version="1.0",
              description="Multilingual AI banking assistant + mock core-banking API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(bank_router)


class ChatReq(BaseModel):
    message: str
    customer_id: str = "CUST001"
    mode: str = "hybrid"
    history: list[dict] = []


@app.on_event("startup")
async def startup():
    c = bank_api.conn()
    if c.execute("select count(*) from customers").fetchone()[0] == 0:
        seed(c)
    from .nlu.intent import get_classifier
    from .rag import search
    get_classifier().predict("warm up")
    search("warm up")
    asyncio.create_task(llm.warmup())


@app.post("/chat", response_model=ChatResult)
async def chat(req: ChatReq):
    mode = "local" if req.mode == "local" else "hybrid"
    return await handle_message(req.message[:2000], req.customer_id, mode, req.history)


@app.get("/customers")
def customers():
    return [{"id": r["id"], "name": r["name"], "preferred_language": r["preferred_language"], "city": r["city"],
             "monthly_income": r["monthly_income"], "credit_score": r["credit_score"],
             "consent": bool(r["consent_personalization"])}
            for r in bank_api.conn().execute("select * from customers order by id limit 12")]


@app.get("/metrics")
def get_metrics():
    return metrics.snapshot()


@app.get("/health")
def health():
    return {"status": "ok"}
