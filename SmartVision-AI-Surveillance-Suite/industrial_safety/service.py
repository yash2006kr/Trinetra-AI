"""Run this surveillance domain as an independent service.

Usage:
    python -m industrial_safety.service
"""

from __future__ import annotations

from industrial_safety.pipeline import IndustrialSafetyPipeline


def main() -> None:
    IndustrialSafetyPipeline().run()


if __name__ == "__main__":
    main()
