"""Punto de entrada del CLI: python -m walopy [--version] <modelo> [parámetros]"""
from __future__ import annotations

import argparse
import sys

from . import __version__
from ._i18n import t as _t


def _add_lam_mu(p: argparse.ArgumentParser) -> None:
    p.add_argument("--lam", type=float, required=True, metavar="LAM",
                   help=_t("main.cli.add_lam_mu.tasa_llegadas"))
    p.add_argument("--mu", type=float, required=True, metavar="MU",
                   help=_t("main.cli.add_lam_mu.tasa_servicio_servidor"))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="walopy",
        description=_t("main.cli.main.herramientas_teoria_colas_investigacion_operaciones"),
    )
    parser.add_argument("--version", action="version", version=_t("main.cli.main.walopy", __version__=__version__))

    sub = parser.add_subparsers(dest="model", metavar="MODELO")

    # --- mm1 ---
    p1 = sub.add_parser("mm1", help=_t("main.cli.main.cola_servidor"))
    _add_lam_mu(p1)

    # --- mmc ---
    pc = sub.add_parser("mmc", help=_t("main.cli.main.cola_varios_servidores"))
    _add_lam_mu(pc)
    pc.add_argument("--c", type=int, required=True, metavar="C", help=_t("main.cli.main.numero_servidores"))

    # --- md1 ---
    pd1 = sub.add_parser("md1", help=_t("main.cli.main.cola_servicio_deterministico"))
    _add_lam_mu(pd1)

    # --- gg1 ---
    pg = sub.add_parser("gg1", help=_t("main.cli.main.aproximacion_kingman"))
    _add_lam_mu(pg)
    pg.add_argument("--ca2", type=float, required=True, metavar="CA2",
                    help=_t("main.cli.main.cv2_tiempos_entre_llegadas"))
    pg.add_argument("--cs2", type=float, required=True, metavar="CS2",
                    help=_t("main.cli.main.cv2_tiempos_servicio"))

    # --- littles ---
    pl = sub.add_parser("littles", help=_t("main.cli.main.resuelve_ley_little_variable_faltante"))
    pl.add_argument("--L",   type=float, default=None, metavar="L")
    pl.add_argument("--lam", type=float, default=None, metavar="LAM")
    pl.add_argument("--W",   type=float, default=None, metavar="W")

    # --- eoq ---
    pe = sub.add_parser("eoq", help=_t("main.cli.main.cantidad_economica_pedido_eoq"))
    pe.add_argument("--demand",   type=float, required=True, metavar="D",
                    help=_t("main.cli.main.tasa_demanda_unidades_periodo"))
    pe.add_argument("--ordering", type=float, required=True, metavar="K",
                    help=_t("main.cli.main.costo_fijo_pedido"))
    pe.add_argument("--holding",  type=float, required=True, metavar="H",
                    help=_t("main.cli.main.costo_mantener_unidad_periodo"))

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
        print(_t("main.cli.main.error", exc=exc), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
