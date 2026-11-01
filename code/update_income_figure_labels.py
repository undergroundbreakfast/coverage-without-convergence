"""Replace two scenario labels in SI Figure 3; retain all numerical drawing content."""

from pathlib import Path
from io import BytesIO
import argparse, json
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from polish_figure_labels import decoded as decode_utf16


def decoded(a, o):
    try:
        return decode_utf16(a, o)
    except UnicodeDecodeError:
        return ""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--font-file", type=Path, help="Optional DejaVuSans.ttf path")
    args = parser.parse_args()
    if args.font_file is None:
        from matplotlib.font_manager import findfont

        font_file = findfont("DejaVu Sans", fallback_to_default=False)
    else:
        font_file = str(args.font_file)
    source, dest = args.source, args.output
    if source.resolve() == dest.resolve():
        raise ValueError("Source and output PDFs must differ.")
    dest.parent.mkdir(parents=True, exist_ok=True)
    replacements = {
        "Odds tilted toward poorer counties": "Odds tilted toward lower income",
        "Odds tilted toward richer counties": "Odds tilted toward higher income",
    }
    r = PdfReader(source)
    w = PdfWriter(clone_from=r)
    page = w.pages[0]
    records = []

    def visitor(t, cm, tm, font, size):
        t = t.strip()
        if t in replacements:
            assert cm[:4] == [1.0, 0.0, 0.0, 1.0] and tm[:4] == [1.0, 0.0, 0.0, 1.0]
            records.append((t, cm[4] + tm[4], cm[5] + tm[5], size))

    page.extract_text(visitor_text=visitor)
    assert len(records) == 2
    cs = page.get_contents()
    ops = []
    block = []
    inside = False
    removed = []
    for args, op in cs.operations:
        if op == b"BT":
            inside = True
            block = []
        if inside:
            block.append((args, op))
        else:
            ops.append((args, op))
        if op == b"ET":
            t = "".join(decoded(a, o) for a, o in block)
            if t in replacements:
                removed.append(t)
            else:
                ops.extend(block)
            inside = False
    assert set(removed) == set(replacements)
    cs.operations = ops
    page.replace_contents(cs)
    pdfmetrics.registerFont(TTFont("ScenarioSans", font_file))
    b = BytesIO()
    c = canvas.Canvas(
        b,
        pagesize=(float(page.mediabox.width), float(page.mediabox.height)),
        invariant=1,
    )
    for t, x, y, size in records:
        right = x + pdfmetrics.stringWidth(t, "ScenarioSans", size)
        c.setFont("ScenarioSans", size)
        c.drawRightString(right, y, replacements[t])
    c.save()
    page.merge_page(PdfReader(b).pages[0])
    w.write(dest)
    old = PdfReader(source).pages[0].extract_text()
    new = PdfReader(dest).pages[0].extract_text()
    for a, b in replacements.items():
        old = old.replace(a, "")
        new = new.replace(b, "")
    assert sorted(old.split()) == sorted(new.split())
    dest.with_suffix(".labels.json").write_text(
        json.dumps(
            {"replacements": replacements, "other_text_retained": True}, indent=2
        )
    )


if __name__ == "__main__":
    main()
