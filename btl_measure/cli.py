from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import compare, load, validate


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="BTL Measure independent evaluation checks")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("validate")
    check.add_argument("file", type=Path)
    paired = sub.add_parser("compare")
    paired.add_argument("baseline", type=Path)
    paired.add_argument("candidate", type=Path)
    paired.add_argument("--minimum-relative-improvement", type=float, default=0.0)
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            result = validate(load(args.file))
        else:
            result = compare(load(args.baseline), load(args.candidate),
                             minimum_relative_improvement=args.minimum_relative_improvement)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if result.get("passed", result.get("comparable", False)) else 2
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(f"btl-measure: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
