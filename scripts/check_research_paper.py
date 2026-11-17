"""Verify the compiled manuscript's citations, links, figures and embedded fonts."""
from pathlib import Path
import re
from urllib.parse import unquote

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/research"


def main():
    source = (DEST / "IsoLab_IEEE.tex").read_text(encoding="utf-8")
    body, bibliography = source.split(r"\begin{thebibliography}{00}")
    def expand_inputs(value):
        return re.sub(r"\\input\{([^}]+)\}", lambda m: expand_inputs(
            (DEST / m.group(1)).read_text(encoding='utf-8')), value)
    body = expand_inputs(body)
    keys = re.findall(r"\\bibitem\{([^}]+)\}", bibliography)
    cited = list(dict.fromkeys(key for group in re.findall(r"\\cite\{([^}]+)\}", body)
                              for key in group.split(",")))
    assert keys == cited, "References must be cited and ordered by first appearance"
    entries = re.split(r"\\bibitem\{[^}]+\}", bibliography)[1:]
    assert all(re.search(r"\\(?:url|href)\{https://", item) for item in entries)
    reader = PdfReader(DEST / "IsoLab_Research_Paper.pdf")
    text = "\n\n".join(page.extract_text() for page in reader.pages)
    for expected in ("Atharva Agrawal", "Niti Priya", "23bds010@iiitdwd.ac.in", "23bcs087@iiitdwd.ac.in"):
        assert expected in text, expected
    annotations = [a.get_object() for page in reader.pages for a in page.get("/Annots", [])]
    uris = {unquote(str(a.get("/A", {}).get("/URI"))) for a in annotations
            if a.get("/A", {}).get("/S") == "/URI"}
    expected_uris = set(re.findall(r"\\(?:url|href)\{(https://[^}]+)\}", source))
    assert expected_uris <= uris, f"Missing external PDF links: {expected_uris - uris}"
    for key in keys:
        assert f"cite.{key}" in reader.named_destinations, f"Missing citation destination: {key}"
    seen = set()
    embedded = {}

    def scan(resources):
        resources = resources.get_object()
        for reference in resources.get("/Font", {}).values():
            font = reference.get_object()
            descendants = font.get("/DescendantFonts")
            data = descendants[0].get_object() if descendants else font
            descriptor = data.get("/FontDescriptor")
            embedded[str(font.get("/BaseFont"))] = bool(descriptor and any(
                k in descriptor.get_object() for k in ("/FontFile", "/FontFile2", "/FontFile3")))
        for reference in resources.get("/XObject", {}).values():
            obj = reference.get_object()
            if id(obj) not in seen and obj.get("/Resources"):
                seen.add(id(obj))
                scan(obj["/Resources"])

    for page in reader.pages:
        assert list(page.mediabox) == [0, 0, 612, 792], "IEEE Letter page size required"
        scan(page["/Resources"])
    assert embedded and all(embedded.values()), "All manuscript and figure fonts must be embedded"
    (DEST / "manuscript.txt").write_text(text, encoding="utf-8")
    print(f"Verified {len(reader.pages)} Letter pages; {len(keys)} linked references; "
          f"{len(annotations)} PDF link annotations; all fonts embedded.")
    expanded = body
    figure_count = expanded.count(chr(92) + 'begin{figure}') + expanded.count(chr(92) + 'begin{figure*}')
    print(f"Figures: {figure_count}; "
          f"tables: {expanded.count(chr(92) + 'begin{table}') + expanded.count(chr(92) + 'begin{table*}')}; authors verified.")


if __name__ == "__main__":
    main()
