"""Run this surveillance domain as an independent service.

Usage:
    python -m smart_parking.service
"""

from __future__ import annotations

from smart_parking.pipeline import SmartParkingPipeline


def main() -> None:
    SmartParkingPipeline().run()


if __name__ == "__main__":
    main()
