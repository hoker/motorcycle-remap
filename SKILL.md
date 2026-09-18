---
name: motorcycle-remap
description: Inspect and patch motorcycle ECU ROMs with tinyrom. Use when remapping, converting unlocked XDF XML to TOML via xdf2toml, tuning fuel/ignition maps, editing rev limiters or flags, comparing ori vs patched bins, or working with .bin/.toml/.xdf ECU files.
---

# Motorcycle remap (tinyrom)

Hands = `tinyrom` library + `scripts/romtool.py`. Brain = this skill.

Do **not** build an MCP for map edit. tinyrom already is the API. MCP only later if another host needs the same tools without a shell.

## Contract

- `tinyrom` owns bytes, TOML, XDF→TOML import, `real = raw * factor + offset`, patch, save.
- Runtime schema is always TOML. Unlocked XDF XML is import only. Never patch against XDF.
- This skill owns workflow, table meaning, safety. Never push policy into `tinyrom`.
- `*-ori.bin` is sacred. Always write a new file. Never flash from the agent.

## Setup

Need Python 3.11+. Dep: [thetinymojo/tinyrom](https://github.com/thetinymojo/tinyrom).

```bash
pip install "git+https://github.com/thetinymojo/tinyrom.git"
```

Escape hatch (dev checkout, no pip): `TINYROM_SRC=/path/to/tinyrom/src`.

From this skill dir (or any cwd with paths to scripts):

```bash
python3 scripts/romtool.py list \
  --bin /path/to/rom.bin --toml /path/to/def.toml
```

User brings own bins/TOML (or unlocked XDF). Example not shipped: `38770-K03-H01-ori.bin` + matching toml.

## Definition (toml or unlocked XDF)

Resolve **one** TOML before any `list`/`dump`/`patch`:

| User has | Action |
|---|---|
| `*.toml` | Use it. |
| unlocked XDF XML (`<XDFFORMAT` in file) | Convert once, then use the TOML. |
| locked/binary `.xdf` (no `<XDFFORMAT`) | Stop. User must unlock, then TunerPro → **XDF XML Definition**. Converter cannot read binary XDF. |
| neither | Stop. Ask for TOML or unlocked XDF XML. |

```bash
python3 scripts/romtool.py xdf2toml \
  --xdf 38770-K03-H01.xdf --out 38770-K03-H01.toml
```

Same converter as `python -m tinyrom.xdf` / `tinyrom-xdf2toml`. Keep the generated TOML next to the bin. Do not treat XDF as runtime schema.

## Job loop

1. **Goal** — user names the change (limiter, fuel region, ignition, flag). Do not invent a power tune.
2. **Def** — toml or `xdf2toml` (above). Then `list` so table keys match this def, not K03 names from [reference.md](reference.md) unless this is that ROM.
3. **Inspect** — `dump`, `flags`, `diff` vs ori. Read [reference.md](reference.md) only for 38770-K03-H01.
4. **Propose** — table, cells/region, old → new, why. Units on this ROM are often **raw**, not ms/AFR. Scale relatively. Do not invent AFR targets.
5. **Wait** — no write until user confirms.
6. **Patch** — `romtool.py patch ... --out <new>.bin`. Then `diff` again.
7. **Stop** — report cell/byte delta. Do not flash. Checksum/verify on bike is the user's job.

## romtool (execute, do not rewrite)

All commands take `--bin` and `--toml` unless noted.

| Cmd | Use |
|---|---|
| `xdf2toml --xdf FILE [--out FILE.toml]` | unlocked XDF XML → TOML. No `--bin`/`--toml`. |
| `list` | tables + shape + min/max |
| `dump --table NAME` | axes + grid. `--csv` for full matrix |
| `flags` | TOML bit flags (tinyrom core does not expose these) |
| `diff --ori A.bin --bin B.bin` | per-table changed cells + byte count |
| `patch --table NAME --out OUT.bin` | see mutators below |
| `flag --name NAME --on\|--off --out OUT.bin` | bit flag |

Patch mutators (one per run):

- `--scale FACTOR` — multiply whole table or `--rows A:B --cols A:B` (half-open)
- `--add DELTA` — add in **real** units
- `--set-cell R,C=VALUE` — repeatable

Refuse patch if `--out` equals the ori path.

## Safety

Hard no without explicit user text:

- overwrite `*-ori.bin`
- disable `bank_angle_sensor_enable`, `injector_enable`
- flash / write ECU
- “max everything” ignition or fuel

Soft no (warn + confirm):

- `ltft_disable` / `o2_feedback_enable` / `o2_sensor_enable` (closed-loop change)
- rev limit above stock fuel limiter without stating the mechanical limit
- ignition add > 2° in any cell
- fuel scale outside 0.95–1.08 in one pass

Stock vs example patch on this ROM: **only** `fuel_rev_limiter` 9600/9800 → ~10500/10550. Four bytes. Use that as the workflow exemplar, not as a recommended street limit.

## API if you must script

```python
from tinyrom import TinyRom
ecu = TinyRom("rom.bin", "def.toml")
m = ecu.get_map("fuel_base_map")   # real units, numpy
ecu.patch_map("fuel_base_map", m * 1.03)
ecu.save("out.bin")
```

Flags are not in `TinyRom`. Use romtool.

## Extra ROM defs

New bike = new unlocked XDF XML → `xdf2toml` → new TOML. Same skill. K03 table names in [reference.md](reference.md) do not apply until `list` proves they match.
