"""Application entrypoint for the AI inference service."""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

DEFAULT_ALLOWED_ORIGINS = {"http://localhost:5173"}
API_PREFIX = os.getenv("API_PREFIX", "/api")

app = FastAPI(title="Neural Network Service")

allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
origins = [
    origin.strip()
    for origin in allowed_origins_env.split(",")
    if origin.strip()
] or list(DEFAULT_ALLOWED_ORIGINS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    prompt: Annotated[str, Field(min_length=1)]
    negative_prompt: str | None = Field(default=None, alias="negativePrompt")
    seed: int | None = None
    num_frames: Annotated[int, Field(ge=1, le=512)] | None = Field(
        default=None, alias="numFrames"
    )

    class Config:
        populate_by_name = True


router = APIRouter(prefix=API_PREFIX)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health")
def api_health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/generate")
def generate_video(payload: GenerateRequest) -> dict[str, str]:
    # Placeholder implementation: replace with Wan2 orchestration logic.
    raise HTTPException(
        status_code=501,
        detail="Wan2 generation endpoint is not implemented yet.",
    )


app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
