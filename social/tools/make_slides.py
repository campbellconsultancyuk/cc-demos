#!/usr/bin/env python3
"""Campbell Consultancy Instagram carousel generator (v2, 2 Nov 2026).

Builds on-brand 1080x1350 JPEG slides from a JSON spec.

Usage:
    python3 make_slides.py spec.json

Requires Pillow, the Inter font (/usr/share/fonts/opentype/inter/), and the
Campbell logo pack from campbellconsultancyuk/campbell-consultancy-site
(public/brand/Campbell_Consultancy_Logo_Pack/02_Horizontal/PNG_Transparent/
horizontal-white-1024px.png).

HOUSE STYLE (default since 2 Nov 2026)
  Backgrounds use the website's hero/footer facet pattern (public/hero-bg.svg),
  remapped to portrait, on the site's dark teal base #082E43, with a horizontal
  teal (#52B7A0) wash. Keep solid navy to a minimum.
    "bg": "feature"  -> wash across the full width, strongest (cover + CTA slides)
    "bg": "pattern"  -> wash starts 45% across, keeps the left dark so teal big
                        numbers and white text stay readable (content slides)
  Legacy (pre-Nov 2026, only for matching old posts): "grad", "deep".

Spec format (see example-glassai.json for the current house style):
{
  "out_dir": "/home/claude/cc-demos/social",
  "prefix": "topic-slide",
  "shots_dir": "/path/to/screenshots",
  "logo": "/path/to/horizontal-white-1024px.png",
  "url_label": "client-site.co.uk",
  "source": "Optional footer line on every slide that sets \"show_source\": true",
  "slides": [
    {"bg": "feature"|"pattern", "label": "01 / 05",
     "bignum": "22",                         # giant teal number above the headline
     "headline": [["text\\n", false], ["italic teal", true]], "size": 76, "top": 300,
     "body": "...", "body_size": 34, "body_weight": "m", "body_colour": "white"|"mute",
     "sub": "smaller second paragraph",
     "show_source": true,
     "browser": "file.png", "browser_crop": 520, "phone": "file.png",
     "stat": ["100", "caption line 1\\nline 2"],
     "quote": ["“Quote.”", "Name, Role, Company", "★★★★★  Google review"],
     "contact": ["Message us", "hello@campbellconsultancy.co", "campbellconsultancy.co"]}
  ]
}

Rules: every stat carries its date/period on the slide (use body or show_source).
Quotes are word-for-word from the proof bank. Real screenshots only.
Screenshots: run the site locally and capture with puppeteer-core plus
@sparticuz/chromium from npm (the Playwright CDN is blocked in the workspace).
Hide cookie banners and floating chat buttons before capturing.
Never recolour or stretch the logo.
"""
import json
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_DIR = '/usr/share/fonts/opentype/inter/'
NAVY, DEEP, TEAL = (19, 36, 80), (8, 31, 76), (82, 183, 160)
SITE_BASE = (8, 46, 67)              # #082E43, base of public/hero-bg.svg
WHITE, MUTE = (255, 255, 255), (176, 190, 214)
W, H = 1080, 1350
FONTS = {'b': 'Inter-Bold.otf', 'sb': 'Inter-SemiBold.otf', 'r': 'Inter-Regular.otf',
         'm': 'Inter-Medium.otf', 'i': 'Inter-BoldItalic.otf'}

# --- website facet pattern (public/hero-bg.svg, 1440x640) -------------------
SX, SY = W / 1440, H / 640
BOOST = 1.35                         # lift light facets a touch for phone screens
POLYS = [
    ((0, 0, 420, 0, 0, 360), '#051F2E', .9), ((1440, 0, 960, 0, 1440, 380), '#051F2E', .9),
    ((0, 640, 280, 640, 0, 420), '#051F2E', .6), ((1440, 640, 1180, 640, 1440, 460), '#051F2E', .6),
    ((200, 0, 500, 0, 340, 200), '#679CAC', .09), ((820, 0, 1120, 0, 970, 170), '#679CAC', .07),
    ((0, 200, 220, 340, 0, 460), '#679CAC', .07), ((1440, 180, 1240, 320, 1440, 440), '#679CAC', .07),
    ((380, 640, 740, 640, 560, 460), '#679CAC', .09),
    ((0, 640, 160, 640, 0, 520), '#679CAC', .18), ((1440, 0, 1440, 160, 1280, 0), '#A8C3CE', .07),
]
LINES = [((0, 540, 360, 0), '#679CAC', .7, .18), ((80, 640, 520, 0), '#679CAC', .4, .11),
         ((820, 0, 1440, 400), '#679CAC', .6, .14), ((1020, 0, 1440, 260), '#A8C3CE', .4, .09)]
DOTS = [(x, y) for y in (80, 560) for x in (80, 160, 240, 1140, 1220, 1300)]
WASH = {'feature': (0.0, 0.7), 'pattern': (0.45, 0.6)}


def font(weight, size):
    return ImageFont.truetype(FONT_DIR + FONTS[weight], size)


def _rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _layer(fn):
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fn(ImageDraw.Draw(lay))
    return lay


def pattern_background(wash_start, wash_max):
    im = Image.new('RGBA', (W, H), SITE_BASE + (255,))
    wash = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(wash)
    for x in range(W):
        t = x / (W - 1)
        a = 0 if t < wash_start else (t - wash_start) / (1 - wash_start)
        d.line([(x, 0), (x, H)], fill=TEAL + (int(255 * wash_max * a),))
    im.alpha_composite(wash)
    for pts, col, op in POLYS:
        xy = [(pts[i] * SX, pts[i + 1] * SY) for i in range(0, len(pts), 2)]
        a = int(255 * min(1, op * (1 if col == '#051F2E' else BOOST)))
        im.alpha_composite(_layer(lambda dr: dr.polygon(xy, fill=_rgb(col) + (a,))))
    for (x1, y1, x2, y2), col, sw, op in LINES:
        a = int(255 * min(1, op * BOOST))
        im.alpha_composite(_layer(lambda dr: dr.line([(x1 * SX, y1 * SY), (x2 * SX, y2 * SY)],
                                                     fill=_rgb(col) + (a,), width=max(1, round(sw * 2.5)))))
    a = int(255 * .14 * BOOST)
    im.alpha_composite(_layer(lambda dr: [dr.ellipse((x * SX - 3, y * SY - 3, x * SX + 3, y * SY + 3),
                                                      fill=_rgb('#A8C3CE') + (a,)) for x, y in DOTS]))
    return im.convert('RGB')


def background(kind):
    if kind in WASH:
        return pattern_background(*WASH[kind])
    if kind == 'grad':                                   # legacy
        im = Image.new('RGB', (W, H))
        d = ImageDraw.Draw(im)
        for x in range(W):
            t = x / (W - 1)
            d.line([(x, 0), (x, H)], fill=tuple(int(NAVY[i] + (TEAL[i] - NAVY[i]) * t) for i in range(3)))
        return im
    return Image.new('RGB', (W, H), DEEP)                # legacy 'deep'


# --- page furniture ---------------------------------------------------------
def shadow(im, box, rad):
    layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
    x, y, x2, y2 = box
    ImageDraw.Draw(layer).rounded_rectangle((x + 10, y + 24, x2 + 10, y2 + 24), rad, fill=(0, 0, 0, 140))
    layer = layer.filter(ImageFilter.GaussianBlur(28))
    im.paste(layer, (0, 0), layer)


def browser(im, path, x, y, w, url_label, crop_h=None):
    s = Image.open(path).convert('RGB')
    s = s.resize((w, int(s.height * w / s.width)), Image.LANCZOS)
    if crop_h:
        s = s.crop((0, 0, w, min(crop_h, s.height)))
    bar = 34
    shadow(im, (x, y, x + w, y + bar + s.height), 14)
    frame = Image.new('RGB', (w, bar + s.height), (236, 238, 241))
    d = ImageDraw.Draw(frame)
    for i, c in enumerate([(255, 95, 87), (254, 188, 46), (40, 200, 64)]):
        d.ellipse((16 + i * 22, 11, 28 + i * 22, 23), fill=c)
    d.rounded_rectangle((110, 7, w - 110, 27), 8, fill=WHITE)
    d.text((w // 2, 17), url_label, fill=(90, 98, 110), font=font('m', 13), anchor='mm')
    frame.paste(s, (0, bar))
    mask = Image.new('L', frame.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, *frame.size), 14, fill=255)
    im.paste(frame, (x, y), mask)
    return y + bar + s.height


def phone(im, path, x, y, w):
    s = Image.open(path).convert('RGB')
    s = s.resize((w - 24, int(s.height * (w - 24) / s.width)), Image.LANCZOS)
    h = s.height + 24
    shadow(im, (x, y, x + w, y + h), 46)
    body = Image.new('RGB', (w, h), (18, 18, 22))
    m = Image.new('L', s.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, *s.size), 34, fill=255)
    body.paste(s, (12, 12), m)
    bm = Image.new('L', (w, h), 0)
    ImageDraw.Draw(bm).rounded_rectangle((0, 0, w, h), 46, fill=255)
    im.paste(body, (x, y), bm)


def headline(d, parts, y, size):
    x = 70
    for text, italic in parts:
        for j, line in enumerate(text.split('\n')):
            if j > 0:
                x, y = 70, y + int(size * 1.12)
            f = font('i' if italic else 'b', size)
            d.text((x, y), line, fill=TEAL if italic else WHITE, font=f)
            x += d.textlength(line, font=f)
    return y + int(size * 1.12)


def paragraph(d, text, y, size, colour, maxw=940, weight='r'):
    f = font(weight, size)
    line = ''
    for word in text.split():
        trial = (line + ' ' + word).strip()
        if d.textlength(trial, font=f) > maxw:
            d.text((70, y), line, fill=colour, font=f)
            y += int(size * 1.45)
            line = word
        else:
            line = trial
    d.text((70, y), line, fill=colour, font=f)
    return y + int(size * 1.45)


def logo(im, path, y):
    lg = Image.open(path).convert('RGBA')
    lg = lg.resize((260, int(lg.height * 260 / lg.width)), Image.LANCZOS)
    im.paste(lg, (70, y), lg)


def build(spec):
    shots = spec.get('shots_dir', '.').rstrip('/') + '/'
    total = len(spec['slides'])
    for n, sl in enumerate(spec['slides'], 1):
        kind = sl.get('bg', 'pattern')
        feature = kind in ('feature', 'grad')
        im = background(kind)
        d = ImageDraw.Draw(im)
        label = sl.get('label', f'{n:02d} / {total:02d}')
        d.text((70, 80), label, fill=WHITE if feature else TEAL, font=font('sb', 24))
        top = sl.get('top', 150 if feature else 130)
        if sl.get('bignum'):
            big = sl['bignum']
            d.text((66, 230), big, fill=TEAL, font=font('b', 250 if len(big) < 4 else 210))
            top = sl.get('top', 560)
        y = headline(d, sl['headline'], top, sl.get('size', 76))
        if sl.get('body'):
            colour = MUTE if sl.get('body_colour', 'white' if feature else 'mute') == 'mute' else WHITE
            y = paragraph(d, sl['body'], y + sl.get('body_gap', 30), sl.get('body_size', 34), colour,
                          weight=sl.get('body_weight', 'm'))
        if sl.get('sub'):
            y = paragraph(d, sl['sub'], y + 20, 32, WHITE if feature else MUTE)
        img_top = max(y + 40, sl.get('img_top', 0))
        if sl.get('browser'):
            bw = sl.get('browser_w', 820 if sl.get('phone') else 940)
            browser(im, shots + sl['browser'], 70, img_top, bw, spec.get('url_label', ''), sl.get('browser_crop'))
        if sl.get('phone'):
            phone(im, shots + sl['phone'], sl.get('phone_x', 730), img_top + sl.get('phone_dy', 90),
                  sl.get('phone_w', 290))
        if sl.get('stat'):
            big, cap = sl['stat']
            d.text((70, H - 200), big, fill=TEAL, font=font('b', 72))
            bx = 70 + d.textlength(big, font=font('b', 72)) + 24
            d.text((bx, H - 188), cap, fill=MUTE, font=font('m', 26), spacing=8)
        if sl.get('quote'):
            q, who, src = sl['quote']
            d.rounded_rectangle((70, y + 40, 1010, y + 280), 24, fill=SITE_BASE)
            d.text((110, y + 80), q, fill=WHITE, font=font('i', 40))
            d.text((110, y + 150), who, fill=TEAL, font=font('sb', 28))
            d.text((110, y + 195), src, fill=MUTE, font=font('m', 26))
            y += 300
        if sl.get('contact'):
            head, *lines = sl['contact']
            yy = y + 90
            d.text((70, yy), head, fill=WHITE, font=font('b', 48))
            for i, line in enumerate(lines):
                d.text((70, yy + 75 + i * 60), line, fill=WHITE if i == 0 else MUTE, font=font('m', 40 if i == 0 else 36))
        if sl.get('show_source') and spec.get('source'):
            d.text((70, H - 205), spec['source'], fill=MUTE, font=font('m', 24))
        logo(im, spec['logo'], H - (90 if sl.get('stat') else 140))
        out = f"{spec['out_dir'].rstrip('/')}/{spec['prefix']}-{n}.jpg"
        im.save(out, quality=90)
        print('wrote', out)


if __name__ == '__main__':
    with open(sys.argv[1]) as fh:
        build(json.load(fh))
