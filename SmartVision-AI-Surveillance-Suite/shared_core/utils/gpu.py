"""GPU and inference runtime helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeDevice:
    device: str
    cuda_available: bool
    half_precision: bool
    backend: str


def resolve_device(requested: str = "auto", use_half_precision: bool = True) -> RuntimeDevice:
    """Return the best available inference device without forcing torch import at startup."""

    try:
        import torch

        cuda = bool(torch.cuda.is_available())
        if requested == "auto":
            device = "cuda:0" if cuda else "cpu"
        else:
            device = requested

        if device.startswith("cuda") and cuda:
            torch.backends.cudnn.benchmark = True
            torch.backends.cuda.matmul.allow_tf32 = True
            half = use_half_precision
        else:
            half = False
        return RuntimeDevice(device=device, cuda_available=cuda, half_precision=half, backend="torch")
    except Exception:
        return RuntimeDevice(device="cpu", cuda_available=False, half_precision=False, backend="none")
