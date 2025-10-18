from __future__ import annotations

import os
import shlex
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Sequence

import yaml


class Wan2GenerationError(RuntimeError):
    """Raised when the Wan2 generation command fails."""


@dataclass
class Wan2LaunchConfig:
    task: str = "t2v-A14B"
    size: str = "1280*720"
    frame_num: int | None = None
    offload_model: bool = True
    convert_model_dtype: bool = True
    additional_args: Sequence[str] | None = None


def load_model_config(config_path: Path) -> Dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Model config {config_path} must contain a mapping.")
    return data


class Wan2Generator:
    """Thin wrapper around Wan2.2's `generate.py` script."""

    def __init__(
        self,
        model_root: Path,
        launch_config: Wan2LaunchConfig,
        output_dir: Path,
        python_executable: str | None = None,
    ) -> None:
        self.model_root = model_root
        self.launch_config = launch_config
        self.output_dir = output_dir
        self.python_executable = python_executable or sys.executable

        self.generate_script = self.model_root / "generate.py"
        if not self.generate_script.exists():
            raise FileNotFoundError(
                f"Expected generate.py at {self.generate_script}. "
                "Ensure the Wan2.2 repo is synced to this path."
            )

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        prompt: str,
        negative_prompt: str | None = None,
        seed: int | None = None,
        num_frames: int | None = None,
        size: str | None = None,
    ) -> Dict[str, Any]:
        save_file = self._build_output_path(prompt)
        cmd = self._build_command(
            prompt=prompt,
            save_file=save_file,
            seed=seed,
            num_frames=num_frames,
            size=size,
        )

        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = os.pathsep.join(
            [pythonpath, str(self.model_root)] if pythonpath else [str(self.model_root)]
        )

        try:
            completed = subprocess.run(
                cmd,
                cwd=self.model_root,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as exc:  # pragma: no cover - subprocess failure path
            raise Wan2GenerationError(
                f"Wan2 generation failed with exit code {exc.returncode}:\n"
                f"STDOUT:\n{exc.stdout}\nSTDERR:\n{exc.stderr}"
            ) from exc

        response: Dict[str, Any] = {
            "status": "completed",
            "output_path": str(save_file),
            "command": shlex.join(cmd),
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
        return response

    def _build_output_path(self, prompt: str) -> Path:
        slug = "_".join(prompt.split()).replace("/", "_")[:48] or "wan2"
        filename = f"{slug}_{uuid.uuid4().hex[:8]}.mp4"
        return (self.output_dir / filename).resolve()

    def _build_command(
        self,
        prompt: str,
        save_file: Path,
        seed: int | None,
        num_frames: int | None,
        size: str | None,
    ) -> list[str]:
        cfg = self.launch_config
        command: list[str] = [
            self.python_executable,
            str(self.generate_script),
            "--task",
            cfg.task,
            "--ckpt_dir",
            str(self.model_root),
            "--prompt",
            prompt,
            "--save_file",
            str(save_file),
        ]

        frame_value = num_frames or cfg.frame_num
        if frame_value is not None:
            command.extend(["--frame_num", str(frame_value)])

        size_value = size or cfg.size
        if size_value:
            command.extend(["--size", size_value])

        if cfg.offload_model:
            command.extend(["--offload_model", "True"])
        if cfg.convert_model_dtype:
            command.append("--convert_model_dtype")

        if seed is not None:
            command.extend(["--base_seed", str(seed)])

        if cfg.additional_args:
            command.extend(cfg.additional_args)

        return command


def build_wan2_generator(
    model_config: Dict[str, Any],
    model_data_dir: Path,
    output_dir: Path,
    python_executable: str | None = None,
) -> Wan2Generator:
    model_section = model_config.get("model", {})
    local_path = model_section.get("local_path")
    if not local_path:
        raise ValueError(
            "Model configuration must define 'model.local_path' pointing to the Wan2 repository."
        )
    model_root = (model_data_dir / local_path).resolve()

    generation_section = model_config.get("generation", {})
    launch_config = Wan2LaunchConfig(
        task=generation_section.get("task", "t2v-A14B"),
        size=generation_section.get("size", "1280*720"),
        frame_num=generation_section.get("frame_num"),
        offload_model=generation_section.get(
            "offload_model", True
        ),
        convert_model_dtype=generation_section.get(
            "convert_model_dtype", True
        ),
        additional_args=generation_section.get("extra_args"),
    )

    return Wan2Generator(
        model_root=model_root,
        launch_config=launch_config,
        output_dir=output_dir,
        python_executable=python_executable,
    )
