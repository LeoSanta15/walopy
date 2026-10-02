"""Punto de entrada del CLI: python -m walopy [--version] <modelo> [parámetros]"""
from __future__ import annotations

import argparse
import sys

from . import __version__


def _add_lam_mu(p: argparse.ArgumentParser) -> None:
    p.add_argument("--lam", type=float, required=True, metavar="LAM",
                   help="Tasa de llegadas λ")
    p.add_argument("--mu", type=float, required=True, metavar="MU",
                   help="Tasa de servicio μ por servidor")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="walopy",
        description="Herramientas de teoría de colas e investigación de operaciones.",
    )
    parser.add_argument("--version", action="version", version=f"walopy {__version__}")

    sub = parser.add_subparsers(dest="model", metavar="MODELO")

    # --- mm1 ---
    p1 = sub.add_parser("mm1", help="Cola M/M/1 de un servidor")
    _add_lam_mu(p1)

    # --- mmc ---
    pc = sub.add_parser("mmc", help="Cola M/M/c de varios servidores")
    _add_lam_mu(pc)
    pc.add_argument("--c", type=int, required=True, metavar="C", help="Número de servidores")

    # --- md1 ---
    pd1 = sub.add_parser("md1", help="Cola M/D/1 con servicio determinístico")
    _add_lam_mu(pd1)

    # --- gg1 ---
    pg = sub.add_parser("gg1", help="Aproximación de Kingman para G/G/1")
    _add_lam_mu(pg)
    pg.add_argument("--ca2", type=float, required=True, metavar="CA2",
                    help="CV² de los tiempos entre llegadas")
    pg.add_argument("--cs2", type=float, required=True, metavar="CS2",
                    help="CV² de los tiempos de servicio")

    # --- littles ---
    pl = sub.add_parser("littles", help="Resuelve la ley de Little para la variable faltante")
    pl.add_argument("--L",   type=float, default=None, metavar="L")
    pl.add_argument("--lam", type=float, default=None, metavar="LAM")
    pl.add_argument("--W",   type=float, default=None, metavar="W")

    # --- eoq ---
    pe = sub.add_parser("eoq", help="Cantidad económica de pedido (EOQ)")
    pe.add_argument("--demand",   type=float, required=True, metavar="D",
                    help="Tasa de demanda (unidades/periodo)")
    pe.add_argument("--ordering", type=float, required=True, metavar="K",
                    help="Costo fijo por pedido")
    pe.add_argument("--holding",  type=float, required=True, metavar="H",
                    help="Costo de mantener por unidad y periodo")

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
