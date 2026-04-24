"""
Tool Forge — describe a tool, get a printable CAD file.

Pipeline:
  user description  ->  Claude generates OpenSCAD code
  OpenSCAD code     ->  optional local OpenSCAD CLI compile to STL
  user downloads    ->  .scad and/or .stl file for their slicer / printer
"""

import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_from_directory
from anthropic import Anthropic

load_dotenv()

app = Flask(__name__)

# ---------- Configuration ----------

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", Path(tempfile.gettempdir()) / "tool_forge_outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Detect OpenSCAD binary for STL conversion (optional).
OPENSCAD_BIN = shutil.which("openscad") or shutil.which("OpenSCAD")

client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None


# ---------- Prompt ----------

SYSTEM_PROMPT = """You are a senior mechanical designer who writes parametric OpenSCAD code for 3D-printable tools and fixtures.

You will be given a short description of a problem or tool. Respond with a single, complete, valid OpenSCAD program that, when rendered, produces a printable solution.

Hard requirements for every response:
1. Output ONLY OpenSCAD code. No prose, no markdown fences, no commentary outside of // comments inside the code.
2. Put all tunable dimensions as named variables at the top of the file, in millimetres, with // comments explaining each.
3. Start with `$fn = 96;` for smooth curves unless a coarser value is intentional.
4. Respect FDM 3D printing reality:
   - Minimum wall thickness 1.6 mm.
   - Avoid unsupported overhangs steeper than 45°; prefer chamfers to overhangs.
   - Flatten one face for the print bed where it makes sense.
   - Add small fillets/chamfers at stress concentrations and sharp corners that contact hands.
   - Keep small features >= 0.8 mm so a 0.4 mm nozzle can resolve them.
5. Use modules for repeated geometry. Use `difference()`, `union()`, `hull()`, `minkowski()` where they make the intent clearer.
6. If the request is ambiguous (e.g. no size given), pick sensible defaults and note them in a header comment block.
7. Include a short // HEADER comment at the top with: tool name, one-line purpose, key dimensions, recommended print orientation, recommended infill %.
8. The final model must be a single manifold solid (or a small number of parts separated along Y axis if multi-part).

Never output anything except the .scad source."""


# ---------- Helpers ----------

_FENCE_RE = re.compile(r"^```(?:openscad|scad)?\s*\n?|\n?```\s*$", re.MULTILINE)


def strip_fences(text: str) -> str:
    """Remove stray markdown fences in case the model adds them."""
    return _FENCE_RE.sub("", text).strip()


def safe_slug(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower()).strip("_")
    return (slug[:max_len] or "tool") + "_" + uuid.uuid4().hex[:6]


def generate_scad(description: str) -> str:
    """Call Claude and return OpenSCAD source."""
    if client is None:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key."
        )

    message = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": description.strip()}],
    )

    # Concatenate any text blocks returned.
    chunks = [b.text for b in message.content if getattr(b, "type", None) == "text"]
    return strip_fences("\n".join(chunks))


def compile_to_stl(scad_path: Path, stl_path: Path) -> tuple[bool, str]:
    """Compile .scad to .stl using the OpenSCAD CLI, if available."""
    if not OPENSCAD_BIN:
        return False, "OpenSCAD binary not found on PATH — STL was not generated."

    try:
        result = subprocess.run(
            [OPENSCAD_BIN, "-o", str(stl_path), str(scad_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return False, "OpenSCAD timed out after 120s."
    except Exception as exc:  # noqa: BLE001
        return False, f"OpenSCAD failed: {exc}"

    if result.returncode != 0:
        # OpenSCAD writes warnings/errors to stderr
        return False, (result.stderr or result.stdout or "OpenSCAD failed.").strip()

    return stl_path.exists(), "" if stl_path.exists() else "OpenSCAD produced no file."


# ---------- Routes ----------


@app.get("/")
def index():
    return render_template(
        "index.html",
        openscad_available=bool(OPENSCAD_BIN),
        api_key_set=bool(ANTHROPIC_API_KEY),
        model=MODEL,
    )


@app.post("/generate")
def generate():
    data = request.get_json(silent=True) or {}
    description = (data.get("description") or "").strip()

    if not description:
        return jsonify({"error": "Please describe the tool or problem."}), 400
    if len(description) > 4000:
        return jsonify({"error": "Description is too long (4000 char max)."}), 400

    try:
        scad_code = generate_scad(description)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Generation failed: {exc}"}), 500

    if not scad_code:
        return jsonify({"error": "Model returned an empty response."}), 500

    slug = safe_slug(description)
    scad_path = OUTPUT_DIR / f"{slug}.scad"
    stl_path = OUTPUT_DIR / f"{slug}.stl"
    scad_path.write_text(scad_code, encoding="utf-8")

    stl_ok, stl_msg = compile_to_stl(scad_path, stl_path)

    return jsonify({
        "scad_code": scad_code,
        "scad_filename": scad_path.name,
        "stl_filename": stl_path.name if stl_ok else None,
        "stl_message": stl_msg,
        "openscad_available": bool(OPENSCAD_BIN),
    })


@app.get("/download/<path:filename>")
def download(filename: str):
    # Prevent path traversal.
    safe_name = Path(filename).name
    return send_from_directory(OUTPUT_DIR, safe_name, as_attachment=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=True)
