"""Run this surveillance domain as an independent service.

Usage:
    python -m traffic_management.service
"""

from __future__ import annotations

from traffic_management.pipeline import TrafficManagementPipeline


def main() -> None:
    TrafficManagementPipeline().run()


if __name__ == "__main__":
    main()
