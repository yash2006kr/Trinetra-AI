"""Run this surveillance domain as an independent service.

Usage:
    python -m railway_surveillance.service
"""

from __future__ import annotations

from railway_surveillance.pipeline import RailwaySurveillancePipeline


def main() -> None:
    RailwaySurveillancePipeline().run()


if __name__ == "__main__":
    main()
