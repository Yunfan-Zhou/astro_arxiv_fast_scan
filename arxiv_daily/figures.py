"""Optional PDF tooling. Selection and visual acceptance belong to the reader."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from .cli import json_text, write_atomic


def inspect_pdf(pdf, output):
    from pypdf import PdfReader
    reader = PdfReader(pdf)
    candidates = []
    for number, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        # Prefer caption-like line starts; do not send every prose reference to the model.
        hits = list(re.finditer(r"^(?:Figure|Fig\.|Table)\s*\d+[a-z]?[.:—]", text, re.I | re.M))
        if hits:
            candidates.append({"page": number, "mentions": [text[m.start():m.end()+500] for m in hits[:12]],
                               "note": "图注候选，须查看原页确认。若无候选，不能据此认定没有图表。"})
    write_atomic(output, json_text({"pdf": str(pdf.resolve()), "pages": len(reader.pages), "candidates": candidates}))


def render_page(pdf, page_number, output, scale=3):
    import pypdfium2 as pdfium
    with pdfium.PdfDocument(pdf) as doc:
        if not 1 <= page_number <= len(doc):
            raise ValueError("page out of range")
        page = doc[page_number - 1]
        bitmap = page.render(scale=scale)
        image = bitmap.to_pil().copy()
        bitmap.close()
        page.close()
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    size = image.size
    image.close()
    return size


def crop_plan(pdf, plan_path, output):
    import pypdfium2 as pdfium
    from PIL import ImageOps
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    items = plan["figures"]
    if not 1 <= len(items) <= 2:
        raise ValueError("Select 1–2 key figures/tables per paper")
    scale = 3  # Fixed 216 dpi. Bounding boxes use rendered pixel coordinates.
    manifest = {"pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(), "scale": scale, "figures": []}
    output.mkdir(parents=True, exist_ok=True)
    with pdfium.PdfDocument(pdf) as doc:
        names = set()
        for item in items:
            name = item["name"]
            if not re.fullmatch(r"[a-zA-Z0-9_-]+", name) or name in names:
                raise ValueError("Figure names must be unique safe basenames")
            names.add(name)
            page_no = item["page"]
            if not isinstance(page_no, int) or not 1 <= page_no <= len(doc):
                raise ValueError("page out of range")
            if not item.get("selection_reason") or not item.get("required_elements"):
                raise ValueError("Record selection reason and all required scientific elements")
            page = doc[page_no - 1]
            bitmap = page.render(scale=scale)
            image = bitmap.to_pil().copy()
            bitmap.close()
            page.close()
            box = item["bbox"]
            if len(box) != 4 or not all(isinstance(v, int) for v in box):
                raise ValueError("bbox must be four integer pixel coordinates")
            left, top, right, bottom = box
            if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
                raise ValueError("Crop outside page bounds")
            cropped = ImageOps.expand(image.crop(box), border=12, fill="white")
            file = output / (name + ".png")
            cropped.save(file)
            manifest["figures"].append({**item, "image": file.name, "rendered_size": list(image.size),
                                         "border_px": 12, "image_sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                                         "visually_verified": False, "verification_note": ""})
            cropped.close()
            image.close()
    # Never carry acceptance forward after recropping.
    write_atomic(output / "manifest.json", json_text(manifest))


def main():
    parser = argparse.ArgumentParser(description="Inspect or crop only selected PDF figures/tables")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("inspect")
    scan.add_argument("pdf", type=Path)
    scan.add_argument("--output", type=Path, required=True)
    render = sub.add_parser("render")
    render.add_argument("pdf", type=Path)
    render.add_argument("--page", type=int, required=True)
    render.add_argument("--output", type=Path, required=True)
    crop = sub.add_parser("crop")
    crop.add_argument("pdf", type=Path)
    crop.add_argument("--plan", type=Path, required=True)
    crop.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "inspect":
        inspect_pdf(args.pdf, args.output)
    elif args.command == "render":
        print(render_page(args.pdf, args.page, args.output))
    else:
        crop_plan(args.pdf, args.plan, args.output)


if __name__ == "__main__":
    main()
