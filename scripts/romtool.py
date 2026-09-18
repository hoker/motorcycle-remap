#!/usr/bin/env python3
"""Inspect / patch ECU bins via tinyrom. See ../SKILL.md."""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path


TINYROM_INSTALL = 'pip install "git+https://github.com/thetinymojo/tinyrom.git"'


def _ensure_tinyrom() -> None:
    try:
        import tinyrom  # noqa: F401
        return
    except ImportError:
        pass

    candidates: list[Path] = []
    if env := os.environ.get("TINYROM_SRC"):
        candidates.append(Path(env))
    skill_root = Path(__file__).resolve().parents[1]
    candidates.extend(
        [
            skill_root.parent.parent / "tinyrom" / "src",
            skill_root.parent / "tinyrom" / "src",
            Path.home() / "Workspace" / "tinyrom" / "src",
        ]
    )
    for path in candidates:
        if (path / "tinyrom" / "__init__.py").is_file():
            sys.path.insert(0, str(path))
            try:
                import tinyrom  # noqa: F401
                return
            except ImportError:
                continue

    raise SystemExit(
        "tinyrom not found. Install from GitHub:\n"
        f"  {TINYROM_INSTALL}\n"
        "Or set TINYROM_SRC=/path/to/tinyrom/src"
    )


_ensure_tinyrom()
import numpy as np  # noqa: E402
from tinyrom import TinyRom  # noqa: E402
from tinyrom.xdf import convert_xdf  # noqa: E402


def _addr(value: str | int) -> int:
    return int(value, 16) if isinstance(value, str) else int(value)


def _load(bin_path: str, toml_path: str) -> TinyRom:
    return TinyRom(bin_path, toml_path)


def _axis(ecu: TinyRom, table: dict, key: str) -> np.ndarray | None:
    axis = table.get(key) or {}
    if "address" not in axis:
        labels = axis.get("labels")
        return np.array(labels) if labels else None
    n = int(axis.get("index_count") or 0)
    if n <= 0:
        return None
    dtype = np.dtype(axis.get("datatype", "u1"))
    addr = _addr(axis["address"])
    raw = np.frombuffer(bytes(ecu.rom[addr : addr + n * dtype.itemsize]), dtype=dtype)
    return raw.astype(float) * axis.get("factor", 1.0) + axis.get("offset", 0.0)


def _fmt_axis(values: np.ndarray | None) -> str:
    if values is None:
        return "-"
    if values.dtype.kind in {"U", "S", "O"}:
        return ", ".join(str(v) for v in values)
    return ", ".join(f"{v:.4g}" for v in values)


def _parse_slice(spec: str | None, n: int) -> slice:
    if not spec:
        return slice(0, n)
    if ":" not in spec:
        i = int(spec)
        return slice(i, i + 1)
    a, b = spec.split(":", 1)
    start = int(a) if a else 0
    stop = int(b) if b else n
    return slice(start, stop)


def _parse_cell(spec: str) -> tuple[int, int, float]:
    rc, _, val = spec.partition("=")
    r_s, _, c_s = rc.partition(",")
    if not (r_s and c_s and val):
        raise ValueError(f"expected R,C=VALUE, got {spec!r}")
    return int(r_s), int(c_s), float(val)


def _flag_byte_mask(flag: dict) -> tuple[int, int]:
    return _addr(flag["address"]), _addr(flag["mask"])


def cmd_list(ecu: TinyRom) -> None:
    print(f"rom_bytes\t{len(ecu.rom)}")
    print(f"tables\t{len(ecu.tables)}")
    for name, table in ecu.tables.items():
        m = ecu.get_map(name)
        print(
            f"{name}\t{table.get('title', '')}\t{m.shape}\t"
            f"{m.min():.6g}\t{m.max():.6g}\t{table.get('units', '')}"
        )


def cmd_dump(ecu: TinyRom, name: str, as_csv: bool) -> None:
    table = ecu.tables[name]
    m = ecu.get_map(name)
    y = _axis(ecu, table, "y_axis")
    x = _axis(ecu, table, "x_axis")
    print(f"table\t{name}")
    print(f"title\t{table.get('title', '')}")
    print(f"shape\t{m.shape}")
    print(f"y\t{_fmt_axis(y)}")
    print(f"x\t{_fmt_axis(x)}")
    if as_csv:
        w = csv.writer(sys.stdout)
        header = [""] + [
            f"{v:.4g}" if not isinstance(v, str) else v
            for v in (x if x is not None else range(m.shape[1]))
        ]
        w.writerow(header)
        for i, row in enumerate(m):
            label = (
                f"{y[i]:.4g}"
                if y is not None and y.dtype.kind not in {"U", "S", "O"}
                else (str(y[i]) if y is not None else str(i))
            )
            w.writerow([label] + [f"{v:.6g}" for v in row])
        return
    np.set_printoptions(linewidth=160, precision=4, suppress=True)
    print(m)


def cmd_flags(ecu: TinyRom) -> None:
    flags = ecu.definition.get("flags") or {}
    if not flags:
        print("no flags in toml")
        return
    for name, flag in flags.items():
        addr, mask = _flag_byte_mask(flag)
        byte = ecu.rom[addr]
        print(
            f"{name}\t{flag.get('title', '')}\t{addr:#06x}\t{mask:#04x}\t"
            f"byte={byte}\t{'on' if byte & mask else 'off'}"
        )


def cmd_diff(ori: TinyRom, pat: TinyRom) -> None:
    if ori.tables.keys() != pat.tables.keys():
        print("table key mismatch", file=sys.stderr)
    for name in ori.tables:
        a, b = ori.get_map(name), pat.get_map(name)
        d = b - a
        n = int((d != 0).sum())
        print(f"{name}\tchanged={n}\tdmin={d.min():.6g}\tdmax={d.max():.6g}")
    n = sum(x != y for x, y in zip(ori.rom, pat.rom))
    extra = abs(len(ori.rom) - len(pat.rom))
    print(f"bytes\tchanged={n}\tsize_delta={extra}")


def _assert_out(out: Path, *forbidden: Path) -> None:
    out = out.resolve()
    for f in forbidden:
        if f.resolve() == out:
            raise SystemExit(f"refusing to overwrite {out}")


def cmd_patch(
    ecu: TinyRom,
    bin_path: Path,
    name: str,
    out: Path,
    scale: float | None,
    add: float | None,
    set_cells: list[str],
    rows: str | None,
    cols: str | None,
) -> None:
    _assert_out(out, bin_path)
    m = ecu.get_map(name).copy()
    sl_r = _parse_slice(rows, m.shape[0])
    sl_c = _parse_slice(cols, m.shape[1])
    if scale is not None:
        m[sl_r, sl_c] = m[sl_r, sl_c] * scale
    if add is not None:
        m[sl_r, sl_c] = m[sl_r, sl_c] + add
    for spec in set_cells:
        r, c, val = _parse_cell(spec)
        m[r, c] = val
    ecu.patch_map(name, m)
    ecu.save(str(out))
    print(f"wrote\t{out}")


def cmd_flag(ecu: TinyRom, bin_path: Path, name: str, on: bool, out: Path) -> None:
    _assert_out(out, bin_path)
    flag = (ecu.definition.get("flags") or {})[name]
    addr, mask = _flag_byte_mask(flag)
    if on:
        ecu.rom[addr] = ecu.rom[addr] | mask
    else:
        ecu.rom[addr] = ecu.rom[addr] & ~mask
    ecu.save(str(out))
    print(f"wrote\t{out}\t{name}={'on' if ecu.rom[addr] & mask else 'off'}")


def cmd_xdf2toml(xdf: Path, out: Path) -> None:
    try:
        convert_xdf(str(xdf), str(out))
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"wrote\t{out}")


def _need_toml(p: argparse.ArgumentParser, toml: str | None) -> str:
    if toml:
        return toml
    p.error("need --toml. If user only has unlocked XDF: xdf2toml --xdf FILE --out FILE.toml")


def main() -> None:
    p = argparse.ArgumentParser(description="tinyrom remap helper")
    p.add_argument("--bin", help="working / patched bin")
    p.add_argument("--toml", help="TinyRom definition (runtime schema)")
    p.add_argument("--ori", help="factory bin (diff)")
    sub = p.add_subparsers(dest="cmd", required=True)

    x2t = sub.add_parser("xdf2toml", help="unlocked XDF XML → TOML")
    x2t.add_argument("--xdf", required=True)
    x2t.add_argument("--out", help="destination .toml (default: xdf stem + .toml)")

    sub.add_parser("list")
    d = sub.add_parser("dump")
    d.add_argument("--table", required=True)
    d.add_argument("--csv", action="store_true")
    sub.add_parser("flags")
    sub.add_parser("diff")

    pt = sub.add_parser("patch")
    pt.add_argument("--table", required=True)
    pt.add_argument("--out", required=True)
    pt.add_argument("--scale", type=float)
    pt.add_argument("--add", type=float)
    pt.add_argument("--set-cell", action="append", default=[], dest="set_cells")
    pt.add_argument("--rows", help="R or A:B (half-open)")
    pt.add_argument("--cols", help="C or A:B (half-open)")

    fl = sub.add_parser("flag")
    fl.add_argument("--name", required=True)
    g = fl.add_mutually_exclusive_group(required=True)
    g.add_argument("--on", action="store_true")
    g.add_argument("--off", action="store_true")
    fl.add_argument("--out", required=True)

    args = p.parse_args()
    if args.cmd == "xdf2toml":
        xdf = Path(args.xdf)
        out = Path(args.out) if args.out else xdf.with_suffix(".toml")
        cmd_xdf2toml(xdf, out)
        return
    toml = _need_toml(p, args.toml)
    if args.cmd != "diff" and not args.bin:
        p.error("--bin required")
    if args.cmd == "diff" and (not args.ori or not args.bin):
        p.error("diff needs --ori and --bin")

    if args.cmd == "list":
        cmd_list(_load(args.bin, toml))
    elif args.cmd == "dump":
        cmd_dump(_load(args.bin, toml), args.table, args.csv)
    elif args.cmd == "flags":
        cmd_flags(_load(args.bin, toml))
    elif args.cmd == "diff":
        cmd_diff(_load(args.ori, toml), _load(args.bin, toml))
    elif args.cmd == "patch":
        if not (args.scale is not None or args.add is not None or args.set_cells):
            p.error("patch needs --scale, --add, or --set-cell")
        cmd_patch(
            _load(args.bin, toml),
            Path(args.bin),
            args.table,
            Path(args.out),
            args.scale,
            args.add,
            args.set_cells,
            args.rows,
            args.cols,
        )
    elif args.cmd == "flag":
        cmd_flag(_load(args.bin, toml), Path(args.bin), args.name, args.on, Path(args.out))


if __name__ == "__main__":
    main()
