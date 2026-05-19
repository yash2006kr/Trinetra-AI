"""Run this surveillance domain as an independent service.

Usage:
    python -m home_security.service
"""

from __future__ import annotations

from home_security.pipeline import HomeSecurityPipeline


def main() -> None:
    HomeSecurityPipeline().run()


if __name__ == "__main__":
    main()
