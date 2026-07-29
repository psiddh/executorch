# Copyright (c) Qualcomm Innovation Center, Inc.
# All rights reserved
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
"""Stable, programmatic entry point for building the QNN LLM deploy graph-set.

External drivers (e.g. the HuggingFace ExecuTorch exporter) call ``build_qnn_llm_graphset`` from
this ``backends/qualcomm`` package instead of importing anything under ``examples/`` (which is not a
stable, shipped API surface). It returns a ``QnnLLMGraphSet`` (the surgered + 16a4w-quantized +
encoding-overridden deploy graphs) *before* lowering, so the caller drives torch.export + to_edge.

NOTE: the underlying static_llama implementation currently lives under
``examples/qualcomm/oss_scripts/llama``. Relocating it into this package (so nothing here imports
``examples``) is the follow-up; this module already gives callers the stable import boundary.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from executorch.examples.qualcomm.oss_scripts.llama import SUPPORTED_LLM_MODELS
from executorch.examples.qualcomm.oss_scripts.llama.llama import _build_parser, export_llama
from executorch.examples.qualcomm.oss_scripts.llama.wrappers.llm_wrappers import QnnLLMGraphSet


__all__ = ["build_qnn_llm_graphset", "resolve_decoder_model", "QnnLLMGraphSet"]

_DEFAULT_SOC_MODEL = "SM8550"
_DEFAULT_PROMPT = "What is the meaning of life?"


def resolve_decoder_model(model: Any = None, decoder_model: Optional[str] = None) -> str:
    """Resolve the static_llama model key from an explicit name, env override, or the model's repo id."""
    if decoder_model:
        return decoder_model
    override = os.environ.get("QNN_DECODER_MODEL")
    if override:
        return override
    repo = getattr(getattr(model, "config", None), "_name_or_path", None)
    for name, cfg in SUPPORTED_LLM_MODELS.items():
        if getattr(cfg, "repo_id", None) and cfg.repo_id == repo:
            return name
    raise ValueError(
        f"Could not map model '{repo}' to a SUPPORTED_LLM_MODELS entry; pass decoder_model "
        "(or set QNN_DECODER_MODEL)."
    )


def build_qnn_llm_graphset(
    model: Any = None,
    *,
    decoder_model: Optional[str] = None,
    soc_model: Optional[str] = None,
    model_mode: str = "kv",
    prompt: Optional[str] = None,
    calib_samples: Optional[str] = None,
    artifact_dir: Optional[str] = None,
) -> QnnLLMGraphSet:
    """Run static_llama surgery + 16a4w PT2E + encoding-override and return the deploy graph-set
    (before lowering). Model-driven: ``model`` supplies the architecture via its config; explicit
    ``decoder_model`` overrides. This is the stable seam a driver reuses instead of touching examples."""
    dm = resolve_decoder_model(model, decoder_model)
    soc = soc_model or os.environ.get("QNN_SOC_MODEL", _DEFAULT_SOC_MODEL)
    artifact = artifact_dir or f"./_qnn_{dm}"
    argv = [
        "--decoder_model", dm,
        "--model_mode", model_mode,
        "--soc_model", soc,
        "--compile_only",
        "-a", artifact,
        "--prompt", prompt or _DEFAULT_PROMPT,
    ]
    if calib_samples:
        argv += ["--calib_samples", calib_samples]
    args = _build_parser().parse_args(argv)
    if args.max_context_len is None:
        args.max_context_len = args.max_seq_len
    return export_llama(args, build_only=True)
