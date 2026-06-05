"""Outreach CLI.

# generate all 5 outreach pieces (no keys needed; uses deterministic template)
python -m outreach run --recipients data/recipients.csv \
    --positioning config/aidentifi_positioning.yaml --out outputs

# use a real LLM for the bespoke tier
OUTREACH_LLM_PROVIDER=anthropic python -m outreach run ...
"""
from __future__ import annotations

import argparse
import json
import sys

from .config import Settings
from .pipeline import run


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="outreach", description="BD outreach generator")
    sub = p.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("run")
    pr.add_argument("--recipients", required=True)
    pr.add_argument("--positioning", required=True)
    pr.add_argument("--out", required=True)
    pr.add_argument("--provider", default=None, choices=["mock", "anthropic", "openai"])
    args = p.parse_args(argv)

    if args.cmd == "run":
        s = Settings()
        if args.provider:
            s.provider = args.provider
        summary = run(args.recipients, args.positioning, args.out, settings=s)
        print(json.dumps(summary, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
