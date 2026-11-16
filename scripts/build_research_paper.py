"""Build the paper with the official IEEEtran conference class.

Use the bundled artifact Python runtime (ReportLab) and Tectonic or pdflatex.
The LaTeX file is the authoritative IEEE manuscript; figures are vector PDFs.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/research"
FIGURE_FONT = "FigureSerif"


def register_figure_font():
    candidates = [Path("C:/Windows/Fonts/times.ttf"),
                  Path("/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf"),
                  Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf")]
    font = next((path for path in candidates if path.is_file()), None)
    if font is None:
        raise RuntimeError("Install Times New Roman, Liberation Serif or DejaVu Serif for embedded figure fonts")
    pdfmetrics.registerFont(TTFont(FIGURE_FONT, str(font)))


def latency_figure():
    evidence = json.loads((DEST / "evidence.json").read_text(encoding="utf-8"))
    source_hash = hashlib.sha256((ROOT / "results/published/e1.json").read_bytes()).hexdigest()
    if source_hash != evidence["sha256"]["e1.json"]:
        raise RuntimeError("Published E1 changed: rerun research_evidence.py and revise manuscript values before building")
    drawing = Drawing(252, 176)
    drawing.initialFontName = FIGURE_FONT
    left, scale = 80, 5.4
    for tick in range(0, 26, 5):
        x = left + tick * scale
        drawing.add(Line(x, 39, x, 154, strokeWidth=.4, strokeColor=colors.HexColor("#cccccc")))
        drawing.add(String(x, 27, str(tick), fontName=FIGURE_FONT, fontSize=8, textAnchor="middle"))
    drawing.add(Line(left + 25 * scale, 39, left + 25 * scale, 154,
                     strokeWidth=.9, strokeColor=colors.black, strokeDashArray=[3, 2]))
    drawing.add(String(left + 25 * scale, 161, "25 ms SLO", fontName=FIGURE_FONT,
                       fontSize=8, textAnchor="middle"))
    for i, (label, profile, arm, color) in enumerate([
        ("Insecure baseline", "insecure", "baseline", "#777777"),
        ("Insecure noisy", "insecure", "noisy", "#777777"),
        ("Hardened baseline", "hardened", "baseline", "#254e70"),
        ("Hardened noisy", "hardened", "noisy", "#254e70"),
    ]):
        row = evidence["profiles"][profile]
        value = row["p99MediansMs"][arm]
        low, high = row["p99RangesMs"][arm]
        y = 133 - 27 * i
        drawing.add(String(0, y + 4, label, fontName=FIGURE_FONT, fontSize=8))
        drawing.add(Rect(left, y, value * scale, 15, fillColor=colors.HexColor(color), strokeColor=None))
        drawing.add(Line(left + low * scale, y + 7.5, left + high * scale, y + 7.5,
                         strokeWidth=.8, strokeColor=colors.black))
        for bound in (low, high):
            drawing.add(Line(left + bound * scale, y + 4, left + bound * scale, y + 11,
                             strokeWidth=.8, strokeColor=colors.black))
        drawing.add(String(left + high * scale + 3, y + 4, f"{value:.3f}",
                           fontName=FIGURE_FONT, fontSize=8))
    drawing.add(String(150, 13, "99th-percentile latency (ms)", fontName=FIGURE_FONT, fontSize=8,
                       textAnchor="middle"))
    drawing.add(String(150, 1, "Whiskers: min-max across three runs", fontName=FIGURE_FONT, fontSize=7,
                       textAnchor="middle"))
    renderPDF.drawToFile(drawing, str(DEST / "ieee-latency.pdf"))


def architecture_figure():
    drawing = Drawing(252, 222)
    drawing.initialFontName = FIGURE_FONT

    def box(x, y, width, height, lines, shade=False):
        drawing.add(Rect(x, y, width, height, fillColor=colors.HexColor("#eeeeee") if shade else colors.white,
                         strokeColor=colors.black, strokeWidth=.6))
        for i, text in enumerate(lines):
            drawing.add(String(x + width / 2, y + height / 2 + (len(lines) - 1) * 4.5 - i * 9 - 2,
                               text, fontName=FIGURE_FONT, fontSize=8, textAnchor="middle"))

    def arrow(x1, y1, x2, y2):
        drawing.add(Line(x1, y1, x2, y2, strokeWidth=.6))
        if y2 < y1:
            points = [x2, y2, x2 - 2.2, y2 + 4, x2 + 2.2, y2 + 4]
        else:
            points = [x2, y2, x2 - 4, y2 - 2.2, x2 - 4, y2 + 2.2]
        drawing.add(Polygon(points, fillColor=colors.black, strokeColor=None))

    for x, label, role in [(2, "Tenant A", "Payments"), (87, "Tenant B", "Batch / noise"),
                           (172, "Tenant C", "Legacy / probes")]:
        box(x, 181, 78, 33, [label, role, "Startup hash gate"])
        arrow(x + 39, 181, x + 39, 169)
    box(2, 142, 248, 27, ["Docker engine and cgroup v2 host interfaces",
                           "Profiles establish tenant boundaries"], True)
    arrow(49, 142, 49, 126)
    arrow(139, 142, 139, 126)
    box(2, 96, 95, 30, ["Restricted API proxy", "Snapshots, stats, events"])
    box(103, 96, 72, 30, ["Read-only mount", "cgroup PSI"])
    box(181, 96, 69, 30, ["Metadata canary", "Authenticated hook"])
    for x in (49, 139, 215):
        arrow(x, 96, x, 73)
    box(2, 46, 248, 27, ["Auditor: checks, attribution, and runtime detections",
                          "Reports, policy gate, and metrics"], True)
    arrow(126, 46, 126, 28)
    box(2, 4, 248, 24, ["Prometheus / Grafana and published results interface"])
    renderPDF.drawToFile(drawing, str(DEST / "ieee-architecture.pdf"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, help="Path to tectonic or pdflatex")
    parser.add_argument("--offline", action="store_true", help="Use only cached Tectonic packages")
    args = parser.parse_args()
    compiler = args.compiler or shutil.which("tectonic") or shutil.which("pdflatex")
    local = ROOT / "tmp/ieee-tools/tectonic/tectonic.exe"
    if compiler is None and local.is_file():
        compiler = local
    if compiler is None:
        parser.error("Tectonic or pdflatex is required; supply --compiler or install it on PATH")
    compiler = Path(compiler).resolve()
    register_figure_font()
    latency_figure()
    architecture_figure()
    source = DEST / "IsoLab_IEEE.tex"
    if "tectonic" in compiler.name.lower():
        options = ["--only-cached"] if args.offline else []
        subprocess.run([str(compiler), *options, "--keep-logs", "--keep-intermediates", str(source)],
                       cwd=DEST, check=True)
    else:
        for _ in range(2):
            subprocess.run([str(compiler), "-interaction=nonstopmode", "-halt-on-error", source.name],
                           cwd=DEST, check=True)
    shutil.copyfile(DEST / "IsoLab_IEEE.pdf", DEST / "IsoLab_Research_Paper.pdf")
    with ZipFile(DEST / "IsoLab_IEEE_Source.zip", "w", compression=ZIP_DEFLATED) as archive:
        for name in ("IsoLab_IEEE.tex", "ieee-architecture.pdf", "ieee-latency.pdf", "IEEE_README.txt"):
            archive.write(DEST / name, arcname=name)
    print(DEST / "IsoLab_Research_Paper.pdf")


if __name__ == "__main__":
    main()
