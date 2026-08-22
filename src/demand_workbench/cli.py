"""Command-line entry points for offline demonstrations and local service."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from demand_workbench import __version__
from demand_workbench.reporting import verify_manifest, write_run_artifacts
from demand_workbench.serialization import run_to_dict
from demand_workbench.service import DemandPlanningService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="demand-workbench")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("doctor", help="Check the local runtime and database.")

    run = commands.add_parser("run", help="Create a forecast run from a UTF-8 CSV file.")
    run.add_argument("--input", type=Path, required=True)
    run.add_argument("--horizon", type=int, default=14)
    run.add_argument("--database", type=Path, default=Path("outputs/workbench.sqlite3"))
    run.add_argument("--output-dir", type=Path, default=Path("outputs/latest"))

    verify = commands.add_parser("verify-output", help="Verify a report manifest and hashes.")
    verify.add_argument("output_dir", type=Path)

    serve = commands.add_parser("serve", help="Start the loopback-only REST API.")
    serve.add_argument("--host", choices=["127.0.0.1", "localhost", "::1"], default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "doctor":
        database = WorkbenchPath.default_database()
        service = DemandPlanningService(database)
        payload = {
            "status": "ok" if service.database.healthcheck() else "degraded",
            "version": __version__,
            "database": str(database),
            "models": [model.name for model in service.forecaster.registry.all()],
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 0

    if args.command == "run":
        if not 1 <= args.horizon <= 90:
            print("horizon must be between 1 and 90", file=sys.stderr)
            return 2
        if not args.input.is_file():
            print(f"input file was not found: {args.input}", file=sys.stderr)
            return 2
        text = args.input.read_text(encoding="utf-8-sig")
        try:
            record = DemandPlanningService(args.database).create_run(
                text, args.horizon, args.input.name
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        manifest = write_run_artifacts(record, args.output_dir)
        summary = run_to_dict(record)
        print(
            json.dumps(
                {
                    "run_id": record.id,
                    "series": len(summary["series"]),
                    "output_dir": str(args.output_dir.resolve()),
                    "manifest_files": len(manifest["files"]),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if args.command == "verify-output":
        valid, errors = verify_manifest(args.output_dir)
        print(json.dumps({"valid": valid, "errors": errors}, ensure_ascii=False))
        return 0 if valid else 1

    if args.command == "serve":
        import uvicorn

        uvicorn.run("demand_workbench.api:app", host=args.host, port=args.port, reload=False)
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")


class WorkbenchPath:
    @staticmethod
    def default_database() -> Path:
        return Path("outputs/workbench.sqlite3")
