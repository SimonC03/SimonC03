"""Builds the profile README: README.md and every SVG panel in assets/.

Edit the content below, then run:  python scripts/build.py   (needs: pip install fonttools)
GitHub images can't load web fonts, so each SVG embeds its own subset of Familjen Grotesk (OFL, see OFL.txt).
"""
import base64, io, pathlib
from html import escape
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

# ---------------------------------------------------------------- content
NAME = "Simon Carlén"
TAGLINE = "Engineer and founder in Gothenburg."
PORTFOLIO = "https://simon-portfolio-wine.vercel.app/en"
EMAIL = "simon.carlen1@gmail.com"

STATEMENT = ("I build AI and software products with Python and TypeScript. Right now that means "
             "CampusLyan, the student housing platform I co-founded and run.")
STATEMENT_LINK = "https://www.campuslyan.se/"

LINKS = [
    ("Portfolio", PORTFOLIO),
    ("LinkedIn", "https://www.linkedin.com/in/simon-carlen/"),
    ("CV", "https://simon-portfolio-wine.vercel.app/en/cv.pdf"),
    ("Email", f"mailto:{EMAIL}"),
]

WORK = [  # (organisation, period, role, description)
    ("CampusLyan", "2025 – now", "Co-founder and CEO",
     "Student housing platform. I own the architecture and much of the code, and the partnerships "
     "with some of Sweden's largest housing companies."),
    ("Chalmers", "2026 – 2028", "M.Sc. Data Science & AI", ""),
    ("Volvo Buses", "Most recently", "Applied AI and machine learning",
     "MCP servers and AI agent tooling, and forecasting models on large-scale bus time-series data."),
]

PROJECTS = [  # (repo, stack, description)
    ("MA-target-scout", "Python · scikit-learn · Streamlit",
     "Finds acquisition candidates that resemble a target profile, weighing industry, margins, "
     "growth and recurring revenue instead of hard filters."),
    ("QuotePredictor", "Python · scikit-learn · Streamlit",
     "Predicts whether a quote will be won. Upload a quote PDF and get a win probability; the model "
     "retrains as new outcomes come in."),
    ("pdf-rag-chat", "Python · FAISS · OpenAI",
     "Ask questions about a PDF. Embeddings run locally, so indexing a document needs no external API."),
]

STACK = [
    ("AI and data", ["Python", "pandas", "scikit-learn", "Time-series forecasting", "RAG", "MCP and AI agents"]),
    ("Product", ["TypeScript", "Next.js", "React", "Node.js", "SQL"]),
    ("Infrastructure", ["Docker", "Google Cloud", "AWS"]),
]
NOTE = ("My background is in automation and mechatronics, which is why the header is a CAN bus frame: "
        "its eight data bytes spell my handle.")
CTA = "Happy to talk about AI, software or building companies."

CAN_ID, CAN_DATA = 0x0C3, b"SimonC03"  # classic CAN frame drawn in the header

# ---------------------------------------------------------------- design
ROOT = pathlib.Path(__file__).resolve().parent.parent
FONT = ROOT / "scripts" / "FamiljenGrotesk.ttf"
FIELD, FIELD_TINT = "#0C4FC4", "#9DBBFF"   # blue field, same in both themes
THEMES = {  # GitHub's own text colours, plus the accent
    "light": dict(ink="#1F2328", muted="#59636E", accent="#0C4FC4"),
    "dark": dict(ink="#F0F6FC", muted="#9198A1", accent="#5C9DFF"),
}
W = 960                     # every panel is drawn at this width and shown at 100%
SEC_TOP = 72                # space above a section heading

_widths = {}


def width(text, size, weight, track=0.0):
    """Advance width of text (no kerning; good enough for wrapping)."""
    if weight not in _widths:
        f = instancer.instantiateVariableFont(TTFont(FONT), {"wght": weight})
        cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
        _widths[weight] = lambda ch: hmtx[cmap[ord(ch)]][0] / upm
    adv = _widths[weight]
    return sum(adv(c) for c in text) * size + track * size * len(text)


def wrap(text, size, weight, maxw):
    lines, cur = [], ""
    for word in text.split():
        cand = f"{cur} {word}".strip()
        if cur and width(cand, size, weight) > maxw:
            lines.append(cur)
            cur = word
        else:
            cur = cand
    return lines + [cur] if cur else lines


def link_width(label):
    return round(width(label, 24, 500) + 26 + 40)  # text, arrow, gap to the next link


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


def heading(svg, text, c):
    y = SEC_TOP + 38
    svg.text(0, y, text, 48, 600, c["ink"], -0.03)
    return y


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


def build_footer():
    h = 250
    s = Svg(f"{CTA} {EMAIL}")
    s.raw(f'<rect width="{W}" height="{h}" fill="{FIELD}"/>')
    s.text(52, 92, CTA, 32, 400, "#fff", -0.01)
    s.text(48, 184, EMAIL, 80, 600, "#fff", -0.035)
    s.write("footer", h)


# ---------------------------------------------------------------- panels
def build_themed(theme, c):
    # Statement: the positioning line, set large
    s = Svg(STATEMENT)
    lines = wrap(STATEMENT, 34, 400, W - 40)
    y = 44
    for ln in lines:
        s.text(0, y, ln, 34, 400, c["ink"], -0.012)
        y += 46
    s.write(f"statement-{theme}", y - 46 + 22)

    # Link buttons: text + arrow, shown at natural size in one row
    for label, _ in LINKS:
        s = Svg(label)
        s.text(0, 30, label, 24, 500, c["accent"], extra=f'<tspan dx="6" font-weight="400">↗</tspan>')
        s.chars.add("↗")
        s.write(f"link-{label.lower()}-{theme}", 44, w=link_width(label))

    # Work: two columns, organisation and period left, role and description right
    s = Svg("Work")
    y = heading(s, "Work", c) + 78
    col = 330
    for org, period, role, desc in WORK:
        s.text(0, y, org, 34, 600, c["ink"], -0.02)
        s.text(0, y + 32, period, 18, 500, c["muted"])
        s.text(col, y, role, 22, 600, c["ink"])
        ly = y + 34
        for ln in wrap(desc, 22, 400, W - col):
            s.text(col, ly, ln, 22, 400, c["ink"])
            ly += 32
        y = max(y + 32 + 18, ly - 32 + 22) + 46
    s.write(f"work-{theme}", y - 46 + 4)

    # Projects: heading, then one clickable panel per repo
    s = Svg("Projects")
    s.write(f"projects-{theme}", heading(s, "Projects", c) + 14)
    for repo, stack, desc in PROJECTS:
        s = Svg(f"{repo}: {desc}")
        y = 40
        s.text(0, y, repo, 34, 600, c["ink"], -0.02,
               extra=f'<tspan dx="10" font-weight="400" fill="{c["accent"]}">↗</tspan>')
        s.chars.add("↗")
        s.text(W, y, stack, 18, 500, c["muted"], anchor="end")
        y += 40
        for ln in wrap(desc, 22, 400, 780):
            s.text(0, y, ln, 22, 400, c["ink"])
            y += 32
        s.write(f"project-{repo.lower()}-{theme}", y - 32 + 18)

    # Stack: three columns, then the personal note
    s = Svg("Stack")
    top = heading(s, "Stack", c) + 62
    colw = W / 3
    bottom = top
    for i, (label, items) in enumerate(STACK):
        x = i * colw
        s.text(x, top, label, 18, 500, c["muted"])
        for j, item in enumerate(items):
            s.text(x, top + 40 + j * 32, item, 22, 400, c["ink"])
        bottom = max(bottom, top + 40 + (len(items) - 1) * 32)
    y = bottom + 76
    for ln in wrap(NOTE, 22, 400, 780):
        s.text(0, y, ln, 22, 400, c["muted"])
        y += 32
    s.write(f"stack-{theme}", y - 32 + 24)


# ---------------------------------------------------------------- README
def pic(name, alt, share=1.0):
    w = f' width="{share * 100:.2f}%"'
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="assets/{name}-dark.svg">'
            f'<img src="assets/{name}-light.svg"{w} alt="{escape(alt)}"></picture>')


def build_readme():
    work_alt = "Work. " + " ".join(f"{o}, {p}: {r}. {d}" for o, p, r, d in WORK)
    stack_alt = "Stack. " + " ".join(f"{l}: {', '.join(i)}." for l, i in STACK) + " " + NOTE
    links = "".join(f'<a href="{u}">{pic(f"link-{l.lower()}", l, link_width(l) / W)}</a>' for l, u in LINKS)
    projects = "\n\n".join(
        f'<a href="https://github.com/SimonC03/{r}">{pic(f"project-{r.lower()}", f"{r} ({st}): {d}")}</a>'
        for r, st, d in PROJECTS)
    md = f"""<!-- Generated by scripts/build.py. Edit the content there and run: python scripts/build.py -->

<a href="{PORTFOLIO}"><img src="assets/header.svg" width="100%" alt="{escape(NAME)}. {escape(TAGLINE)} Below the name runs a CAN bus frame whose eight data bytes spell SimonC03."></a>

<a href="{STATEMENT_LINK}">{pic("statement", STATEMENT)}</a>

{links}

{pic("work", work_alt)}

{pic("projects", "Projects")}

{projects}

{pic("stack", stack_alt)}

<br>

<a href="mailto:{EMAIL}"><img src="assets/footer.svg" width="100%" alt="{escape(CTA)} {EMAIL}"></a>
"""
    (ROOT / "README.md").write_text(md, encoding="utf-8")


if __name__ == "__main__":
    for old in (ROOT / "assets").glob("*.svg"):
        old.unlink()
    build_header()
    build_footer()
    for theme, colours in THEMES.items():
        build_themed(theme, colours)
    build_readme()
    print("built", len(list((ROOT / "assets").glob("*.svg"))), "SVGs and README.md")
