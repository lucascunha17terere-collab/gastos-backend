from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any
import datetime, os
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://nsnjtjueoqsccdcwkspn.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

app = FastAPI(title="gastos sync")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_sb():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

class SyncPayload(BaseModel):
    items: list[dict[str, Any]]

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.datetime.now().isoformat()}

@app.post("/sync")
def sync(payload: SyncPayload):
    sb = get_sb()
    synced = 0
    for item in payload.items:
        t = item.get("type")
        data = item.get("data", {})
        try:
            if t == "gasto":
                sb.table("gastos").upsert({
                    "id": data.get("id"),
                    "valor": data.get("valor", 0),
                    "descricao": data.get("desc", ""),
                    "cat": data.get("cat", "outros"),
                    "tipo": data.get("tipo", "saida"),
                    "data": data.get("data", ""),
                    "synced": True,
                    "via_ia": data.get("viaIA", False)
                }).execute()
                synced += 1
            elif t == "lembrete":
                sb.table("lembretes").upsert({
                    "id": data.get("id"),
                    "texto": data.get("texto", ""),
                    "detalhe": data.get("detalhe", ""),
                    "prioridade": data.get("prioridade", "med"),
                    "done": data.get("done", False),
                    "data": data.get("data", ""),
                    "synced": True,
                    "via_ia": data.get("viaIA", False)
                }).execute()
                synced += 1
            elif t == "lembrete_update":
                sb.table("lembretes").update({
                    "done": data.get("done", False)
                }).eq("id", data.get("id")).execute()
                synced += 1
        except Exception as e:
            print(f"sync error: {e}")
    return {"ok": True, "synced": synced, "total": len(payload.items)}

@app.get("/data")
def get_data():
    sb = get_sb()
    gastos = sb.table("gastos").select("*").order("data", desc=True).execute().data
    lembretes = sb.table("lembretes").select("*").order("data", desc=True).execute().data
    for g in gastos:
        g["desc"] = g.pop("descricao", "")
    return {"gastos": gastos, "lembretes": lembretes}

@app.delete("/gasto/{gasto_id}")
def delete_gasto(gasto_id: str):
    sb = get_sb()
    sb.table("gastos").delete().eq("id", gasto_id).execute()
    return {"ok": True}

@app.delete("/lembrete/{lem_id}")
def delete_lembrete(lem_id: str):
    sb = get_sb()
    sb.table("lembretes").delete().eq("id", lem_id).execute()
    return {"ok": True}
