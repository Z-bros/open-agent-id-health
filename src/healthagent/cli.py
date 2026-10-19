"""Offline CLI demo."""
import argparse
import json
from pathlib import Path
from .synthetic import SyntheticRepository
from .workflow import Investigator

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "synthetic" / "records.json"

def main():
    parser = argparse.ArgumentParser(description="Synthetic evidence investigation demo")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--case", help="Synthetic case identifier")
    group.add_argument("--list", action="store_true", help="List synthetic cases")
    args = parser.parse_args()
    repo = SyntheticRepository(DATA_PATH)
    if args.list:
        for case in repo.cases.values():
            print(f"{case.case_id}: {case.workflow}")
        return
    case = repo.cases.get(args.case)
    if case is None:
        parser.error(f"Unknown case {args.case!r}; use --list")
    print(json.dumps(Investigator(repo).run(case).to_dict(), indent=2))

if __name__ == "__main__":
    main()
