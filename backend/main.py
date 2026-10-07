"""Small Google Fact Check proxy for a separate Render web service."""

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


def missing_configuration() -> list[str]:
    """Report missing variable names without exposing their values."""
    return [name for name in ("GOOGLE_FACT_CHECK_API_KEY", "FACTCHECK_PROXY_TOKEN") if not os.getenv(name)]


@app.api_route("/", methods=["GET", "HEAD"])
def health():
    missing = missing_configuration()
    return {"status": "misconfigured" if missing else "ok", "missing_env": missing}


@app.post("/fact-check")
async def fact_check(request: FactCheckRequest, authorization: str | None = Header(default=None)):
    missing = missing_configuration()
    if missing:
        raise HTTPException(status_code=503, detail=f"Configuração ausente no Render: {', '.join(missing)}")
    proxy_token = os.environ["FACTCHECK_PROXY_TOKEN"]
    api_key = os.environ["GOOGLE_FACT_CHECK_API_KEY"]
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
