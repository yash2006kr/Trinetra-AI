"""Run this surveillance domain as an independent service.

Usage:
    python -m campus_security.service
"""

from __future__ import annotations

from campus_security.pipeline import CampusSecurityPipeline


def main() -> None:
    CampusSecurityPipeline().run()


if __name__ == "__main__":
    main()
