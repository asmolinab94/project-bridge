"""Project Bridge CLI: `python3 run.py --data <input folder> --out <output folder>`."""

import argparse
import os
import sys

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import bridge  # noqa: E402
from bridge import report  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description="Reconcile the card programme and propose the September close.")
    parser.add_argument("--data", required=True, help="folder with the input files (read only)")
    parser.add_argument("--out", required=True, help="folder for the ten output files (created if missing)")
    args = parser.parse_args(argv)
    report.write(bridge.build(args.data), args.out, REPO_ROOT)
    print("Wrote the output files to %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
