"""Builds assets/header.svg, the banner at the top of the README.

Edit the text below, then run:  python scripts/build.py   (needs: pip install fonttools)
GitHub images can't load web fonts, so the SVG embeds its own subset of Familjen Grotesk (OFL, see OFL.txt).
"""
import base64, io, pathlib
from html import escape
from fontTools import subset
from fontTools.ttLib import TTFont

NAME = "Simon Carlén"
TAGLINE = "Engineer and founder in Gothenburg."
CAN_ID, CAN_DATA = 0x0C3, b"SimonC03"  # classic CAN frame drawn in the header

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONT = ROOT / "scripts" / "FamiljenGrotesk.ttf"
FIELD, FIELD_TINT = "#0C4FC4", "#9DBBFF"
W = 960


def font_face(chars):
    f = TTFont(FONT)
    opts = subset.Options()
    opts.layout_features = ["*"]
    opts.hinting = False
    s = subset.Subsetter(opts)
    s.populate(text="".join(sorted(set(chars))))
    s.subset(f)
    f.flavor = "woff"
    buf = io.BytesIO()
    f.save(buf)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f'@font-face {{ font-family: "FG"; font-weight: 400 700; src: url(data:font/woff;base64,{b64}) format("woff"); }}'


class Svg:
    def __init__(self, title):
        self.title, self.parts, self.chars = title, [], set()

    def text(self, x, y, s, size, weight=400, fill="#000", track=0.0, anchor="start", extra=""):
        self.chars.update(s)
        anchor = f' text-anchor="{anchor}"' if anchor != "start" else ""
        style = f' style="letter-spacing:{track}em"' if track else ""
        self.parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" '
                          f'fill="{fill}"{anchor}{style}>{escape(s)}{extra}</text>')

    def raw(self, s):
        self.parts.append(s)

    def write(self, name, h, w=W, scale=1.0):
        body = "\n  ".join(self.parts)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h:.0f}" '
               f'width="{w * scale:.0f}" height="{h * scale:.0f}" role="img">\n'
               f'  <title>{escape(self.title)}</title>\n'
               f'  <style>{font_face(self.chars)}\n'
               f'    text {{ font-family: "FG", "Helvetica Neue", Arial, sans-serif; }}</style>\n'
               f'  {body}\n</svg>\n')
        (ROOT / "assets" / f"{name}.svg").write_text(svg, encoding="utf-8")


# ---------------------------------------------------------------- CAN frame
def bits(v, n):
    return [(v >> (n - 1 - i)) & 1 for i in range(n)]


def crc15(bs):
    crc = 0
    for b in bs:
        nxt = b ^ ((crc >> 14) & 1)
        crc = (crc << 1) & 0x7FFF
        if nxt:
            crc ^= 0x4599
    return crc


assert crc15([b for c in b"123456789" for b in bits(c, 8)]) == 0x059E  # CRC-15/CAN check value


def can_frame():
    fields = [("sof", [0]), ("id", bits(CAN_ID, 11)), ("ctrl", [0, 0, 0] + bits(len(CAN_DATA), 4))]
    fields += [(f"d{i}", bits(c, 8)) for i, c in enumerate(CAN_DATA)]
    crc = crc15([b for _, bs in fields for b in bs])
    fields.append(("crc", bits(crc, 15)))
    seq, run_v, run_n = [(1, "idle")] * 4, None, 0
    for name, bs in fields:
        for b in bs:
            seq.append((b, name))
            run_n = run_n + 1 if b == run_v else 1
            run_v = b
            if run_n == 5:  # bit stuffing: complement after five equal bits
                seq.append((1 - b, name))
                run_v, run_n = 1 - b, 1
    stuffed = [v for v, _ in seq[4:]]
    assert all(len(set(stuffed[i:i + 6])) == 2 for i in range(len(stuffed) - 5)), "stuffing broken"
    seq += [(1, "crcdel"), (0, "ack"), (1, "ackdel")] + [(1, "eof")] * 7 + [(1, "idle")] * 4
    return seq, crc


def build_header():
    seq, crc = can_frame()
    h, x0, x1, mid, amp = 476, 52, 908, 344, 34
    bw = (x1 - x0) / len(seq)

    def trace(sign):
        y = lambda v: mid + sign * amp if v == 0 else mid
        pts, prev = [(x0, y(seq[0][0]))], seq[0][0]
        for i, (v, _) in enumerate(seq):
            if v != prev:
                x = x0 + i * bw
                pts += [(x, y(prev)), (x + bw * 0.22, y(v))]
                prev = v
        pts.append((x1, y(prev)))
        return "M" + " L".join(f"{x:.1f} {yy:.0f}" for x, yy in pts)

    def centre(name):
        idx = [i for i, (_, f) in enumerate(seq) if f == name]
        return x0 + (idx[0] + idx[-1] + 1) / 2 * bw

    s = Svg(f"{NAME}. {TAGLINE}")
    s.raw(f'<rect width="{W}" height="{h}" fill="{FIELD}"/>')
    s.text(42, 184, NAME, 158, 600, "#fff", -0.045)
    s.text(52, 244, TAGLINE, 32, 400, "#fff", -0.01)
    style = 'fill="none" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"'
    s.raw(f'<path {style} stroke="{FIELD_TINT}" d="{trace(+1)}"/>')
    s.raw(f'<path {style} stroke="#fff" d="{trace(-1)}"/>')
    labels = [("id", f"ID {CAN_ID:03X}"), ("ctrl", f"DLC {len(CAN_DATA)}")]
    for i, c in enumerate(CAN_DATA):
        s.text(centre(f"d{i}"), 426, chr(c), 26, 500, "#fff", anchor="middle")
    for name, t in labels + [("crc", f"CRC {crc:04X}"), ("ack", "ACK")]:
        s.text(centre(name), 426, t, 17, 500, FIELD_TINT, anchor="middle")
    s.write("header", h)


if __name__ == "__main__":
    build_header()
    print("built assets/header.svg")
