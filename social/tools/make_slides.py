#!/usr/bin/env python3
"""Campbell Consultancy Instagram carousel generator.

Builds on-brand 1080x1350 JPEG slides from a JSON spec.

Usage:
    python3 make_slides.py spec.json

Requires Pillow, the Inter font (/usr/share/fonts/opentype/inter/), and the
Campbell logo pack from campbellconsultancyuk/campbell-consultancy-site
(public/brand/). Set the paths in the spec if they differ.

Spec format (see example-archetype.json):
{
  "out_dir": "/home/claude/cc-demos/social",
  "prefix": "archetype-slide",
  "shots_dir": "/path/to/screenshots",
  "logo": "/path/to/horizontal-white-1024px.png",
  "url_label": "archetype-studio.uk",
  "slides": [
    {"bg": "grad"|"deep", "label": "...", "headline": [["text\\n", false], ["italic teal", true]],
     "size": 76, "body": "...", "browser": "file.png", "browser_crop": 520,
     "phone": "file.png", "stat": ["100", "caption line 1\\nline 2"],
     "quote": ["“Quote.”", "Name, Role, Company", "★★★★★  Google review"],
     "contact": ["Message us", "hello@campbellconsultancy.co", "campbellconsultancy.co"]}
  ]
}

Screenshots: run the site locally and capture with puppeteer-core plus
@sparticuz/chromium from npm (the Playwright CDN is blocked in the workspace).
Hide cookie banners and floating chat buttons before capturing.
Brand: navy #132450, deep navy #081F4C, teal #52B7A0. The gradient runs
horizontally only, navy to teal. Never recolour or stretch the logo.
"""
import json
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_DIR = '/usr/share/fonts/opentype/inter/'
NAVY, DEEP, TEAL = (19, 36, 80), (8, 31, 76), (82, 183, 160)
WHITE, MUTE = (255, 255, 255), (176, 190, 214)
W, H = 1080, 1350
FONTS = {'b': 'Inter-Bold.otf', 'sb': 'Inter-SemiBold.otf', 'r': 'Inter-Regular.otf',
         'm': 'Inter-Medium.otf', 'i': 'Inter-BoldItalic.otf'}


def font(weight, size):
    return ImageFont.truetype(FONT_DIR + FONTS[weight], size)


def background(kind):
    if kind != 'grad':
        return Image.new('RGB', (W, H), DEEP)
    im = Image.new('RGB', (W, H))
    d = ImageDraw.Draw(im)
    for x in range(W):
        t = x / (W - 1)
        d.line([(x, 0), (x, H)], fill=tuple(int(NAVY[i] + (TEAL[i] - NAVY[i]) * t) for i in range(3)))
    return im


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


def paragraph(d, text, y, size, colour, maxw=940):
    f = font('r', size)
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
        grad = sl.get('bg', 'deep') == 'grad'
        im = background('grad' if grad else 'deep')
        d = ImageDraw.Draw(im)
        label = sl.get('label', f'{n:02d} / {total:02d}')
        d.text((70, 80), label, fill=WHITE if grad else TEAL, font=font('sb', 24))
        y = headline(d, sl['headline'], sl.get('top', 150 if grad else 130), sl.get('size', 76))
        if sl.get('body'):
            y = paragraph(d, sl['body'], y + 15, sl.get('body_size', 30 if not grad else 32),
                          WHITE if grad else MUTE)
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
            d.rounded_rectangle((70, y + 40, 1010, y + 280), 24, fill=DEEP)
            d.text((110, y + 80), q, fill=WHITE, font=font('i', 40))
            d.text((110, y + 150), who, fill=TEAL, font=font('sb', 28))
            d.text((110, y + 195), src, fill=MUTE, font=font('m', 26))
            y += 300
        if sl.get('contact'):
            head, *lines = sl['contact']
            yy = y + 60
            d.text((70, yy), head, fill=WHITE, font=font('b', 48))
            for i, line in enumerate(lines):
                d.text((70, yy + 70 + i * 55), line, fill=WHITE, font=font('m', 38))
        logo(im, spec['logo'], H - (90 if sl.get('stat') else 110))
        out = f"{spec['out_dir'].rstrip('/')}/{spec['prefix']}-{n}.jpg"
        im.save(out, quality=90)
        print('wrote', out)


if __name__ == '__main__':
    with open(sys.argv[1]) as fh:
        build(json.load(fh))
