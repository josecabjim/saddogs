from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from supabase import create_client
from env import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
from typing import Any

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

app = FastAPI()


class CensusItem(BaseModel):
    no_canario: int
    el_hierro: int
    fuerteventura: int
    gran_canaria: int
    la_gomera: int
    la_palma: int
    lanzarote: int
    tenerife: int
    year: int
    month: int
    day: int


@app.post("/census", status_code=201)
async def create_census(item: CensusItem):
    try:
        response = supabase.table("census").insert(item.dict()).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if getattr(response, "error", None):
        msg = (
            response.error.get("message")
            if isinstance(response.error, dict)
            else str(response.error)
        )
        raise HTTPException(status_code=400, detail=msg)

    return {"data": getattr(response, "data", None)}


@app.get("/census", response_model=Any)
async def get_all_census():
    try:
        response = supabase.table("census").select("*").execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if getattr(response, "error", None):
        msg = (
            response.error.get("message")
            if isinstance(response.error, dict)
            else str(response.error)
        )
        raise HTTPException(status_code=400, detail=msg)

    return {"data": getattr(response, "data", None)}
