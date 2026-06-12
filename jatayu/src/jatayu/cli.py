"""Jatayu CLI.

Examples
--------
# offline demo (no keys, no credits) - produces every deliverable from fixtures
python -m jatayu run --mandate config/mandate_a_compliance_sg.yaml \
    --out deliverables/mandate_a

# live production pull (needs CORESIGNAL_API_KEY + JATAYU_MODE=live in .env)
JATAYU_MODE=live python -m jatayu run \
    --mandate config/mandate_a_compliance_sg.yaml --out deliverables/mandate_a

# show the compiled Coresignal ES query without running anything
python -m jatayu show-query --mandate config/mandate_a_compliance_sg.yaml
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import Settings, load_mandate
from .filters import build_es_query
from .pipeline import run


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="jatayu", description="Sourcing & ranking tool")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="run the full pipeline")
    p_run.add_argument("--mandate", required=True, help="path to mandate YAML")
    p_run.add_argument("--out", required=True, help="output directory for deliverables")
    p_run.add_argument("--stage", default="production", choices=["dev", "production"])
    p_run.add_argument("--mode", default=None, choices=["offline", "live"],
                       help="override JATAYU_MODE")

    p_q = sub.add_parser("show-query", help="print the compiled Coresignal ES query")
    p_q.add_argument("--mandate", required=True)

    p_p = sub.add_parser("preview", help="cheap dev filter-validation (1 credit live, 0 offline)")
    p_p.add_argument("--mandate", required=True)
    p_p.add_argument("--mode", default=None, choices=["offline", "live"])

    args = parser.parse_args(argv)

    if args.cmd == "preview":
        from .coresignal_client import make_client
        from .credit_ledger import CreditLedger
        cfg = load_mandate(args.mandate)
        settings = Settings()
        if args.mode:
            settings.mode = args.mode
        settings.autoselect_fixtures(cfg)
        ledger = CreditLedger()
        client = make_client(settings, ledger, stage="dev")
        result = client.preview(cfg["filter"], purpose="dev:filter-validation")
        print(json.dumps({"preview": result, "credits_spent": ledger.total_spent,
                          "mode": settings.mode}, indent=2))
        return 0

    if args.cmd == "show-query":
        cfg = load_mandate(args.mandate)
        print(json.dumps(build_es_query(cfg["filter"]), indent=2))
        return 0

    if args.cmd == "run":
        settings = Settings()
        if args.mode:
            settings.mode = args.mode
        summary = run(args.mandate, args.out, settings=settings, stage=args.stage)
        print(json.dumps(summary, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
