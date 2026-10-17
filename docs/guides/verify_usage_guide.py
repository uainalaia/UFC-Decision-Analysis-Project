"""Artifact QA for the Spanish guide; leaves the application untouched."""

import hashlib
import json
from pathlib import Path

import pdfplumber
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/pdf"
PDF = OUT / "MMA_Decision_Lab_Guia_Visual_de_Uso.pdf"
ASSETS = OUT / "assets"
reader = PdfReader(PDF)
assert len(reader.pages) == 20
assert len(reader.outline) == 20
with pdfplumber.open(PDF) as doc:
    texts = [p.extract_text() or "" for p in doc.pages]
    text = "\n".join(texts)
    assert all(len(t) > 350 for t in texts)
    assert "\ufffd" not in text
    for i, t in enumerate(texts, 1):
        assert f"{i:02d} / 20" in t
    for label in ["Fight brief", "Fighter evidence", "Tactical model", "Outcome analysis",
                  "Sensitivity", "Validation", "Research report", "Methodology"]:
        assert label in text
    for expected in ["70,37 %", "68,79 %", "+1,57 pp", "527", "0,2425", "57,1 %",
                     "0,0969", "0,1318", "No robust tactical preference"]:
        assert expected in text, expected
    assert "≈" in text
    page_details = [{"page": i + 1, "characters": len(texts[i]),
                     "images": len(p.images), "width_pt": p.width, "height_pt": p.height}
                    for i, p in enumerate(doc.pages)]

expected_destinations = [4, 5, 6, 9, 12, 16]
destinations = []
for reference in reader.pages[1]["/Annots"]:
    annotation = reference.get_object()
    if "/Dest" in annotation:
        target = annotation["/Dest"][0].idnum
        page_index = next(i for i, p in enumerate(reader.pages)
                          if p.indirect_reference.idnum == target)
        destinations.append(page_index + 1)
assert destinations == expected_destinations

trace = json.loads((ASSETS / "layout_trace.json").read_text(encoding="utf-8"))
assert min(b[2] for b in trace["blocks"]) >= 60
scientific_integrity = json.loads((ROOT / "reports/audit_v2/final_integrity.json").read_text())
for relative, record in scientific_integrity["files"].items():
    assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == record["expected"]

example = json.loads((ASSETS / "guide_example.json").read_text(encoding="utf-8"))
assert example["model_sha256"] == hashlib.sha256((ROOT / "models/baseline.json").read_bytes()).hexdigest()
rendered = list((ROOT / "tmp/pdfs/usage_guide").glob("page-*.png"))
assert len(rendered) == 20
result = {"status": "passed", "page_count": 20,
          "pdf_sha256": hashlib.sha256(PDF.read_bytes()).hexdigest(),
          "pdf_bytes": PDF.stat().st_size,
          "outline_entries": len(reader.outline),
          "internal_route_destinations": destinations,
          "minimum_tracked_block_bottom_pt": min(b[2] for b in trace["blocks"]),
          "rendered_pages": len(rendered),
          "source_model_and_dataset_unchanged": True,
          "page_details": page_details}
(ASSETS / "guide_quality_checks.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({k: v for k, v in result.items() if k != "page_details"}, indent=2))
