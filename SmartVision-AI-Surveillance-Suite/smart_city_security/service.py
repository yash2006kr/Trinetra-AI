"""Run this surveillance domain as an independent service.

Usage:
    python -m smart_city_security.service
"""

from __future__ import annotations

from smart_city_security.pipeline import SmartCitySecurityPipeline


def main() -> None:
    SmartCitySecurityPipeline().run()


if __name__ == "__main__":
    main()
