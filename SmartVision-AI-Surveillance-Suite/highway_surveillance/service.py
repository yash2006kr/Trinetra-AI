"""Run this surveillance domain as an independent service.

Usage:
    python -m highway_surveillance.service
"""

from __future__ import annotations

from highway_surveillance.pipeline import HighwaySurveillancePipeline


def main() -> None:
    HighwaySurveillancePipeline().run()


if __name__ == "__main__":
    main()
