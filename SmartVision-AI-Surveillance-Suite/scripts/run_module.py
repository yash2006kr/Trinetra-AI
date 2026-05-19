"""Run a SmartVision module by name."""

from __future__ import annotations

import argparse
from importlib import import_module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("module", help="Module package name, e.g. highway_surveillance")
    args = parser.parse_args()
    service = import_module(f"{args.module}.service")
    service.main()


if __name__ == "__main__":
    main()
