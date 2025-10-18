"""Application entrypoint for the AI inference service."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Any, Dict

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .services.wan2 import (
    Wan2GenerationError,
    build_wan2_generator,
    load_model_config,
)

DEFAULT_ALLOWED_ORIGINS = {"http://localhost:5173"}
API_PREFIX = os.getenv("API_PREFIX", "/api")

MODEL_CONFIG_PATH = Path(
    os.getenv("MODEL_CONFIG", "configs/model.example.yaml")
).resolve()
MODEL_DATA_DIR = Path(os.getenv("MODEL_DATA_DIR", "/models")).resolve()
OUTPUT_VIDEO_DIR = Path(
    os.getenv("OUTPUT_VIDEO_DIR", "outputs")
).resolve()

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

try:
    MODEL_CONFIG = load_model_config(MODEL_CONFIG_PATH)
    WAN2_GENERATOR = build_wan2_generator(
        model_config=MODEL_CONFIG,
        model_data_dir=MODEL_DATA_DIR,
        output_dir=OUTPUT_VIDEO_DIR,
    )
except Exception as exc:  # pragma: no cover - fail fast during startup
    raise RuntimeError(
        f"Failed to initialise Wan2 generator: {exc}"
    ) from exc


class GenerateRequest(BaseModel):
    prompt: Annotated[str, Field(min_length=1)]
    negative_prompt: str | None = Field(default=None, alias="negativePrompt")
    seed: int | None = None
    num_frames: Annotated[int, Field(ge=1, le=512)] | None = Field(
        default=None, alias="numFrames"
    )
    size: str | None = None

    class Config:
        populate_by_name = True


class GenerationResponse(BaseModel):
    status: str
    output_path: str
    download_url: str
    command: str
    stdout: str | None = None
    stderr: str | None = None


router = APIRouter(prefix=API_PREFIX)


@app.get("/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok"}


@router.get("/health")
def api_health_check() -> Dict[str, str]:
    return {"status": "ok"}


@router.post("/generate", response_model=GenerationResponse)
def generate_video(payload: GenerateRequest) -> GenerationResponse:
    try:
        result = WAN2_GENERATOR.generate(
            prompt=payload.prompt,
            negative_prompt=payload.negative_prompt,
            seed=payload.seed,
            num_frames=payload.num_frames,
            size=payload.size,
        )
    except Wan2GenerationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    output_path = Path(result["output_path"]).resolve()
    download_url = f"{API_PREFIX}/outputs/{output_path.name}"

    return GenerationResponse(
        status=result.get("status", "completed"),
        output_path=str(output_path),
        download_url=download_url,
        command=result.get("command", ""),
        stdout=result.get("stdout"),
        stderr=result.get("stderr"),
    )


@router.get("/outputs/{filename}")
def download_output(filename: str) -> Any:
    safe_name = Path(filename).name
    file_path = OUTPUT_VIDEO_DIR / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Output not found")
    return FileResponse(file_path)


app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
