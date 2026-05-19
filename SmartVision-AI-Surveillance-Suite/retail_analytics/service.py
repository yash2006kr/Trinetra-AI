"""Run this surveillance domain as an independent service.

Usage:
    python -m retail_analytics.service
"""

from __future__ import annotations

from retail_analytics.pipeline import RetailAnalyticsPipeline


def main() -> None:
    RetailAnalyticsPipeline().run()


if __name__ == "__main__":
    main()
