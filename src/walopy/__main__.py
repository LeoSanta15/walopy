"""CLI entry point: python -m walopy [--version] <model> [params]"""
from __future__ import annotations

import argparse
import sys

from . import __version__


def _add_lam_mu(p: argparse.ArgumentParser) -> None:
    p.add_argument("--lam", type=float, required=True, metavar="LAM",
                   help="Arrival rate λ")
    p.add_argument("--mu", type=float, required=True, metavar="MU",
                   help="Service rate μ per server")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="walopy",
        description="Queuing theory and operations analysis toolkit.",
    )
    parser.add_argument("--version", action="version", version=f"walopy {__version__}")

    sub = parser.add_subparsers(dest="model", metavar="MODEL")

    # --- mm1 ---
    p1 = sub.add_parser("mm1", help="M/M/1 single-server queue")
    _add_lam_mu(p1)

    # --- mmc ---
    pc = sub.add_parser("mmc", help="M/M/c multi-server queue")
    _add_lam_mu(pc)
    pc.add_argument("--c", type=int, required=True, metavar="C", help="Number of servers")

    # --- md1 ---
    pd1 = sub.add_parser("md1", help="M/D/1 deterministic service queue")
    _add_lam_mu(pd1)

    # --- gg1 ---
    pg = sub.add_parser("gg1", help="G/G/1 Kingman approximation")
    _add_lam_mu(pg)
    pg.add_argument("--ca2", type=float, required=True, metavar="CA2",
                    help="Squared CV of inter-arrival times")
    pg.add_argument("--cs2", type=float, required=True, metavar="CS2",
                    help="Squared CV of service times")

    # --- littles ---
    pl = sub.add_parser("littles", help="Solve Little's Law for the missing variable")
    pl.add_argument("--L",   type=float, default=None, metavar="L")
    pl.add_argument("--lam", type=float, default=None, metavar="LAM")
    pl.add_argument("--W",   type=float, default=None, metavar="W")

    # --- eoq ---
    pe = sub.add_parser("eoq", help="Economic Order Quantity")
    pe.add_argument("--demand",   type=float, required=True, metavar="D",
                    help="Demand rate (units/period)")
    pe.add_argument("--ordering", type=float, required=True, metavar="K",
                    help="Fixed cost per order")
    pe.add_argument("--holding",  type=float, required=True, metavar="H",
                    help="Holding cost per unit per period")

    args = parser.parse_args(argv)

    if args.model is None:
        parser.print_help()
        sys.exit(0)

    try:
        if args.model == "mm1":
            from .queuing import mm1
            print(mm1(args.lam, args.mu).summary())

        elif args.model == "mmc":
            from .queuing import mmc
            print(mmc(args.lam, args.mu, args.c).summary())

        elif args.model == "md1":
            from .queuing import md1
            print(md1(args.lam, args.mu).summary())

        elif args.model == "gg1":
            from .queuing import kingman
            print(kingman(args.lam, args.mu, args.ca2, args.cs2).summary())

        elif args.model == "littles":
            from .queuing import littles_law
            result = littles_law(L=args.L, lam=args.lam, W=args.W)
            missing = [k for k, v in {"L": args.L, "lam": args.lam, "W": args.W}.items() if v is None]
            print(f"{missing[0]} = {result:.6g}")

        elif args.model == "eoq":
            from .inventory import eoq
            print(eoq(args.demand, args.ordering, args.holding).summary())

    except (ValueError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
