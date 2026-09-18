# motorcycle-remap

Agent skill for motorcycle ECU remap with [tinyrom](https://github.com/thetinymojo/tinyrom).

Inspect maps, convert unlocked XDF → TOML, patch bins, diff vs factory. No flash. No proprietary ROMs in this repo.

## Requirements

- Python 3.11+
- [tinyrom](https://github.com/thetinymojo/tinyrom)

```bash
pip install "git+https://github.com/thetinymojo/tinyrom.git"
```

Dev checkout without pip:

```bash
export TINYROM_SRC=/path/to/tinyrom/src
```

## Install this skill

After you push this repo to GitHub:

```bash
npx skills add <owner>/<repo>
# example if repo is thetinymojo/motorcycle-remap:
npx skills add thetinymojo/motorcycle-remap -g
```

Local only:

```bash
ln -s "$(pwd)" ~/.cursor/skills/motorcycle-remap
```

## Usage

User supplies `.bin` + `.toml`, or unlocked XDF XML.

```bash
python3 scripts/romtool.py list --bin rom.bin --toml def.toml
python3 scripts/romtool.py xdf2toml --xdf unlocked.xdf --out def.toml
python3 scripts/romtool.py dump --bin rom.bin --toml def.toml --table fuel_base_map
python3 scripts/romtool.py diff --ori stock.bin --bin patched.bin --toml def.toml
```

See `SKILL.md` for agent workflow + safety. See `reference.md` for Honda 38770-K03-H01 notes.

## Layout

```text
SKILL.md           # agent instructions
reference.md       # example ROM table notes
scripts/romtool.py # list / dump / patch / flags / xdf2toml
README.md
```

## License / data

Do not commit ECU `.bin`, locked `.xdf`, passwords, or vendor dumps. Definitions you own may be shared as `.toml` if clean.
