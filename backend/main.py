"""Google Fact Check proxy for deployment as a separate Render service."""

import os
import secrets

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Fact Check Backend")
GOOGLE_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"


class FactCheckRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    pageSize: int = Field(default=10, ge=1, le=10)
    languageCode: str = Field(default="pt", pattern=r"^pt$")
    pageToken: str | None = Field(default=None, max_length=2048)


@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/fact-check")
async def fact_check(request: FactCheckRequest, authorization: str | None = Header(default=None)):
    proxy_token = os.getenv("FACTCHECK_PROXY_TOKEN")
    api_key = os.getenv("GOOGLE_FACT_CHECK_API_KEY")
    if not proxy_token or not api_key:
        raise HTTPException(status_code=503, detail="Serviço não configurado")
    if not authorization or not secrets.compare_digest(authorization, f"Bearer {proxy_token}"):
        raise HTTPException(status_code=401, detail="Não autorizado")

    params = {
        "query": request.query,
        "pageSize": request.pageSize,
        "languageCode": request.languageCode,
        "key": api_key,
    }
    if request.pageToken:
        params["pageToken"] = request.pageToken

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(GOOGLE_URL, params=params)
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("claims", []), list):
            raise ValueError("Invalid Google response")
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        raise HTTPException(
            status_code=status if status in {400, 401, 403, 429} else 502,
            detail="Erro ao consultar Google Fact Check",
        ) from None
    except (httpx.HTTPError, ValueError):
        raise HTTPException(status_code=502, detail="Erro ao consultar Google Fact Check") from None

    return payload
