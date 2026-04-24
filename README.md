# TOOL / FORGE

Describe a tool or a problem in plain English. Get a parametric CAD file
(`.scad`, and optionally `.stl`) you can slice and 3D-print.

Under the hood it's a small Flask app that asks Claude to write
**OpenSCAD** code — a parametric, script-based CAD format — then (if
OpenSCAD is installed locally) compiles it to STL.

---

## 1. Install

You need Python 3.10+ and, optionally but recommended, **OpenSCAD**.

### Python

```bash
# from the project directory
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### OpenSCAD (optional — needed for automatic STL export)

- **macOS:** `brew install --cask openscad`
- **Windows:** download from https://openscad.org/downloads.html
- **Linux:** `sudo apt install openscad` or use the AppImage

Make sure `openscad` is on your PATH. Verify with:

```bash
openscad --version
```

If OpenSCAD isn't installed the app still works — it just gives you the
`.scad` file, which you can open in OpenSCAD (or any compatible viewer)
and export to STL yourself.

---

## 2. Configure

Copy the example env file and add your Anthropic API key:

```bash
cp .env.example .env
# edit .env and paste your key after ANTHROPIC_API_KEY=
```

Get a key at https://console.anthropic.com.

---

## 3. Run

```bash
python app.py
```

Open http://127.0.0.1:5000 in your browser.

---

## 4. Use

1. Describe the tool or the problem it solves. Be specific where it
   matters — the object it interacts with, dimensions you know, how it
   mounts or grips. Leave the rest to the model.
2. Hit **Forge** (or Ctrl/Cmd+Enter).
3. Review the generated OpenSCAD code. It's fully parametric — the
   tunable dimensions are named variables at the top of the file.
4. Download `.scad` (always available) and `.stl` (if OpenSCAD is
   installed).
5. Slice the STL and print.

### Tips for good descriptions

- **Name the mating part.** "Fits a 22 mm round hose" is better than
  "fits a hose".
- **Say how it attaches.** Screws? 3M tape? Clips? Press-fit?
- **Say where the load goes.** Downward pull, twisting, impact.
- **Call out constraints.** "Must fit inside a drawer 40 mm tall."
- **Leave the rest.** The model picks sensible defaults and notes them
  in a comment block at the top of the file.

### Example prompts

> A desk-edge cable comb for six USB-C cables, clamps onto a 22 mm thick
> desk edge with a single thumb-screw, cables sit in round channels
> 5.5 mm across so they can be lifted out.

> A jig for drilling two parallel 4 mm pilot holes 32 mm apart, with a
> flange that hooks over a shelf edge so the holes land 12 mm below the
> top surface.

> A replacement foot for an IKEA Poäng chair — 26 mm outer diameter
> cylindrical socket, 40 mm tall total, felt recess 2 mm deep on the
> floor-contact face.

---

## 5. Editing the output

Every generated file is parametric. Open the `.scad` in OpenSCAD
(F5 preview, F6 render, then File → Export → STL) and change the
variables at the top to tweak dimensions without regenerating.

---

## Project layout

```
tool-forge/
├── app.py                 Flask backend + Claude call + OpenSCAD shell-out
├── requirements.txt
├── .env.example
├── templates/
│   └── index.html         UI
└── static/
    ├── style.css
    └── script.js
```

## Troubleshooting

- **"API missing key" badge in top right** — put your key in `.env`.
- **"OpenSCAD offline" badge** — install OpenSCAD and make sure it's on
  your PATH, or just download the `.scad` file and convert manually.
- **Generated part won't print / has overhangs** — tell the model about
  the orientation you want and re-forge, or edit the `.scad` directly.
- **Want a different Claude model** — set `CLAUDE_MODEL` in `.env`
  (e.g. `claude-opus-4-7` for higher quality, `claude-haiku-4-5-20251001`
  for speed).
