from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .accounting import (
    classify_accounting,
    load_chart_of_accounts,
    post_to_odoo,
    refresh_chart_of_accounts,
    validate_result,
)
from .extraction import extract_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OpenClaw Odoo accounting CLI")
    parser.add_argument("document", type=Path, help="Path to receipt/invoice file (.pdf, image, .txt)")
    parser.add_argument("--coa", type=Path, required=True, help="Path to chart of accounts JSON")
    parser.add_argument("--api-key", default="", help="Odoo API key (required only with --allow-post)")
    parser.add_argument("--default-currency", default="USD", help="Fallback currency code")
    parser.add_argument("--refresh-coa-cmd", default="", help="Shell command to refresh COA JSON")
    parser.add_argument("--output", type=Path, default=Path("accounting_result.json"), help="Result output file")
    parser.add_argument("--allow-post", action="store_true", help="Attempt to post to Odoo")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        if args.refresh_coa_cmd:
            refresh_chart_of_accounts(args.coa, args.refresh_coa_cmd)

        coa = load_chart_of_accounts(args.coa)
        raw_text, extraction_mode = extract_text(args.document)
        result = classify_accounting(raw_text, coa, default_currency=args.default_currency)
        result.notes = f"{result.notes}; extraction_mode={extraction_mode}"
        validate_result(result, coa)

        post_response = post_to_odoo(result, api_key=args.api_key, dry_run=not args.allow_post)
        output_payload = result.as_json()
        output_payload["post_response"] = post_response
        args.output.write_text(json.dumps(output_payload, indent=2), encoding="utf-8")

        print(json.dumps(output_payload, indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
