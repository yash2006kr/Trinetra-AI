"""Run this surveillance domain as an independent service.

Usage:
    python -m wildlife_monitoring.service
"""

from __future__ import annotations

from wildlife_monitoring.pipeline import WildlifeMonitoringPipeline


def main() -> None:
    WildlifeMonitoringPipeline().run()


if __name__ == "__main__":
    main()
