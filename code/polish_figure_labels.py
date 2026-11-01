"""Adjust figure-panel typography while retaining scientific drawing content.

Requires the original vector PDFs and a local Arial font directory. No fonts
are distributed with this software. Only the specified text objects are changed."""

from pathlib import Path
from io import BytesIO
import argparse, json, shutil
from collections import Counter
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import pypdfium2 as pdfium

HERE = Path(__file__).resolve().parent
PUBLICATION_WIDTH = 180 / 25.4 * 72


def decoded(args, op):
    if op not in (b"TJ", b"Tj"):
        return ""
    strings = args[0] if op == b"TJ" else args
    return "".join(
        getattr(x, "original_bytes", x).decode("utf-16be")
        for x in strings
        if hasattr(x, "original_bytes") or isinstance(x, bytes)
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--font-dir", type=Path, required=True)
    args = ap.parse_args()
    if args.source.resolve() == args.output.resolve():
        raise ValueError("Source and output directories must differ.")
    if not list(args.source.glob("*.pdf")):
        raise FileNotFoundError("No source PDFs found.")
    args.output.mkdir(parents=True, exist_ok=True)
    pdfmetrics.registerFont(TTFont("PanelArial", str(args.font_dir / "Arial.ttf")))
    pdfmetrics.registerFont(
        TTFont("PanelArialBold", str(args.font_dir / "Arial Bold.ttf"))
    )
    qa = args.output / "qa"
    qa.mkdir(parents=True, exist_ok=True)
    report = {}
    for source in sorted(args.source.glob("*.pdf")):
        target = args.output / source.name
        stem = source.stem
        reader = PdfReader(source)
        writer = PdfWriter(clone_from=reader)
        page = writer.pages[0]
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        scale = width / PUBLICATION_WIDTH
        labelsize = 8 * scale
        titlesize = 7 * scale
        selected = {
            "Figure_1": ["a", "b", "c", "d"],
            "Figure_2": ["a", "b"],
            "Figure_3": ["a", "b"],
            "Supplementary_Figure_2": ["a  2022", "b  2024"],
            "Supplementary_Figure_3": ["a  RUCC 4-6", "b  RUCC 7-9"],
            "Supplementary_Figure_5": [
                "a",
                "b",
                "c",
                "b  Appalachia",
                "c  Lower Mississippi",
                "d  Residents by proximity category",
                "Reported stage within 30 proxy minutes",
            ],
            "Supplementary_Figure_6": [
                "a",
                "b",
                "Expanding or fully integrated",
                "Fully integrated",
            ],
        }.get(stem, [])
        if not selected:
            shutil.copy2(source, target)
            report[stem] = {
                "changed": False,
                "reason": "No lettered panels; existing layout retained.",
            }
        else:
            records = []

            def visit(text, cm, tm, font, size):
                text = text.strip()
                if text in selected and (font and "Bold" in str(font)):
                    assert cm[:4] == [1.0, 0.0, 0.0, 1.0] and tm[:4] == [
                        1.0,
                        0.0,
                        0.0,
                        1.0,
                    ]
                    records.append((text, cm[4] + tm[4], cm[5] + tm[5]))

            page.extract_text(visitor_text=visit)
            assert Counter(t for t, x, y in records) == Counter(selected), (
                stem,
                records,
            )
            stream = page.get_contents()
            oldops = stream.operations
            newops = []
            block = []
            inside = False
            removed = []
            fonts = page["/Resources"]["/Font"]
            for operands, operator in oldops:
                if operator == b"BT":
                    inside = True
                    block = []
                if inside:
                    block.append((operands, operator))
                else:
                    newops.append((operands, operator))
                if operator == b"ET":
                    text = "".join(decoded(a, o) for a, o in block)
                    fontrefs = [a[0] for a, o in block if o == b"Tf"]
                    isbold = any(
                        "Bold" in str(fonts[f].get_object().get("/BaseFont"))
                        for f in fontrefs
                    )
                    if text in selected and isbold:
                        removed.append((text, block))
                    else:
                        newops.extend(block)
                    inside = False
            assert Counter(t for t, b in removed) == Counter(selected), (stem, removed)
            # No map, curve, bar, axis, number or clipping operations are edited.
            assert len(oldops) - len(newops) == sum(len(b) for t, b in removed)
            stream.operations = newops
            page.replace_contents(stream)
            buf = BytesIO()
            c = canvas.Canvas(
                buf,
                pagesize=(width, height),
                pageCompression=1,
                invariant=1,
                initialFontName="PanelArial",
                initialFontSize=titlesize,
            )

            def panel(letter, title, x, y, size=labelsize):
                c.setFont("PanelArialBold", size)
                c.drawString(x, y, letter)
                if title:
                    c.setFont("PanelArial", titlesize)
                    c.drawString(
                        x
                        + pdfmetrics.stringWidth(letter, "PanelArialBold", size)
                        + 4 * scale,
                        y,
                        title,
                    )

            for text, x, y in records:
                if stem == "Supplementary_Figure_6":
                    if text in ("a", "b"):
                        continue
                    panel("a" if text.startswith("Expanding") else "b", text, x, y)
                elif (
                    stem == "Supplementary_Figure_5"
                    and text == "Reported stage within 30 proxy minutes"
                ):
                    c.setFont("PanelArialBold", titlesize)
                    c.drawString(x, y, text)
                else:
                    pieces = text.split("  ", 1)
                    letter = pieces[0]
                    title = pieces[1] if len(pieces) > 1 else ""
                    size = labelsize
                    if stem == "Supplementary_Figure_5":
                        if text == "a":
                            y = next(
                                yy for t, xx, yy in records if t == "b  Appalachia"
                            )
                        elif text in ("b", "c"):
                            size = titlesize  # map-window locators, not panel headers
                    panel(letter, title, x, y, size)
            c.save()
            page.merge_page(PdfReader(buf).pages[0])
            writer.add_metadata(
                {
                    "/Title": stem.replace("_", " "),
                    "/Subject": "Panel typography polished; scientific drawing content preserved",
                }
            )
            with target.open("wb") as f:
                writer.write(f)
            # Text content is identical, allowing the deliberately separated headers.
            oldwords = Counter("".join(p.extract_text() for p in reader.pages).split())
            newwords = Counter(
                "".join(p.extract_text() for p in PdfReader(target).pages).split()
            )
            # reader's page was edited in place; a fresh source supplies the reference.
            oldwords = Counter(PdfReader(source).pages[0].extract_text().split())
            assert oldwords == newwords, (
                stem,
                oldwords - newwords,
                newwords - oldwords,
            )
            report[stem] = {
                "changed": True,
                "replaced_text_objects": len(removed),
                "panel_font": "Arial Bold",
                "label_pt_at_180mm": 8,
                "context_font": "Arial",
                "context_pt_at_180mm": 7,
                "all_other_drawing_operations_retained": True,
            }
        with pdfium.PdfDocument(target) as d:
            d[0].render(scale=1000 / d[0].get_width()).to_pil().save(
                qa / (target.stem + ".png")
            )
    (qa / "typography_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
