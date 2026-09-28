#!/usr/bin/env python3
"""Rebuild the gallery assets and metadata from the paper's appendix gallery.

The page shows the same curated static-vs-ReCAST pairs the paper does, with the
same prompts and reward budgets, so the two should not be maintained by hand in
two places. This script is the one-way sync: paper -> page.

It does three things:

1. Converts ``figures/appendix_gallery/{ocr,geneval}/*.png`` to WebP. The
   source PNGs are 512x512 and ~360 kB each; at quality 90 the 40 of them go
   from 14.4 MB to 2.4 MB, which matters for a repo that GitHub Pages serves.
2. Rasterizes the paper figures the page embeds. They are vector PDFs, and
   ``<img>`` cannot use a PDF, so each is rendered at a zoom chosen to land
   around 2000 px wide.
3. Parses the prompt and lambda budget out of the two ``*_figure.tex`` files
   into ``static/data/gallery.json``, which the page's JS reads.

Usage (from this repo's root):

    python3 scripts/extract_gallery.py --paper /path/to/writing/TWDNFT

Needs Pillow and PyMuPDF. If the layout of the appendix gallery .tex files
changes, the asserts below will fail loudly rather than emit a half-built
gallery.
"""

import argparse
import json
import os
import re
import sys

SETTINGS = [
    {"key": "ocr", "label": "OCR setting",
     "lambda_order": ["ClipScore", "HPSv2", "PickScore", "OCR"]},
    {"key": "geneval", "label": "GenEval setting",
     "lambda_order": ["ClipScore", "HPSv2", "PickScore", "GenEval"]},
]

# paper figure (without .pdf) -> (page image name, zoom factor)
#
# The results section deliberately embeds no figure: the paper reports its results
# as tables, and figures/performance2.pdf, despite the name, is a base-model radar
# chart that is not \includegraphics'd anywhere in the paper.
FIGURES = {
    "renyi_omega":          ("method_gain_curves", 3.0),
    "renyi_omega_combined": ("ablation_psampling", 2.0),
}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def convert_gallery(paper, root):
    from PIL import Image

    src_total = out_total = 0
    for setting in SETTINGS:
        src_dir = os.path.join(paper, "figures", "appendix_gallery", setting["key"])
        out_dir = os.path.join(root, "static", "images", "gallery", setting["key"])
        os.makedirs(out_dir, exist_ok=True)
        for name in sorted(os.listdir(src_dir)):
            if not name.endswith(".png"):
                continue
            src = os.path.join(src_dir, name)
            out = os.path.join(out_dir, name[:-4] + ".webp")
            Image.open(src).convert("RGB").save(out, "WEBP", quality=90, method=6)
            src_total += os.path.getsize(src)
            out_total += os.path.getsize(out)
    print(f"gallery images: {src_total / 1e6:.1f} MB png -> {out_total / 1e6:.1f} MB webp")


def convert_figures(paper, root):
    import pymupdf

    out_dir = os.path.join(root, "static", "images")
    os.makedirs(out_dir, exist_ok=True)
    for stem, (out_name, zoom) in FIGURES.items():
        src = os.path.join(paper, "figures", stem + ".pdf")
        if not os.path.exists(src):
            print(f"  skipped {stem}.pdf (not found)")
            continue
        doc = pymupdf.open(src)
        pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        pix.save(os.path.join(out_dir, out_name + ".png"))
        print(f"  {stem}.pdf -> {out_name}.png  ({pix.width}x{pix.height})")


def parse_pairs(paper, setting):
    """The prompts and budgets for one setting, in the paper's own order.

    Each gallery row is a line of four \\includegraphics followed by a line of
    two \\multicolumn cells, one caption per image pair.
    """
    path = os.path.join(paper, "figures", "appendix_gallery",
                        setting["key"] + "_figure.tex")
    tex = open(path).read()
    pending, entries = None, []
    for line in tex.splitlines():
        imgs = re.findall(r"appendix_gallery/%s/([A-Za-z0-9_]+)\.png" % setting["key"], line)
        if imgs:
            assert len(imgs) == 4, f"{path}: expected 4 images per row, got {len(imgs)}"
            pending = imgs
            continue
        if r"\multicolumn" in line:
            assert pending, f"{path}: caption row before any image row"
            prompts = re.findall(r"\\emph\{(.*?)\}\\\\", line)
            lams = re.findall(r"\\bm\{\\lambda\}=\(([\d,]+)\)", line)
            assert len(prompts) == 2 and len(lams) == 2, \
                f"{path}: expected 2 captions per row, got {len(prompts)}/{len(lams)}"
            for k in (0, 1):
                base, ours = pending[2 * k], pending[2 * k + 1]
                assert base.endswith("baseline") and ours.endswith("sinkhorn"), \
                    f"{path}: pair order is not (baseline, sinkhorn): {base}, {ours}"
                entries.append({
                    "lambda": "(" + lams[k] + ")",
                    "prompt": prompts[k].strip(),
                    "static": base + ".webp",
                    "recast": ours + ".webp",
                })
            pending = None
    assert entries, f"{path}: no pairs parsed"
    return entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", required=True,
                    help="path to the paper source dir (writing/TWDNFT)")
    ap.add_argument("--skip-images", action="store_true",
                    help="rebuild gallery.json only")
    args = ap.parse_args()

    paper = os.path.abspath(args.paper)
    if not os.path.isdir(os.path.join(paper, "figures")):
        sys.exit(f"no figures/ under {paper}")

    if not args.skip_images:
        convert_gallery(paper, ROOT)
        convert_figures(paper, ROOT)

    data = {
        "_note": "Generated by scripts/extract_gallery.py from the paper's "
                 "appendix gallery. Do not edit by hand.",
        "settings": SETTINGS,
        "pairs": {s["key"]: parse_pairs(paper, s) for s in SETTINGS},
    }
    out = os.path.join(ROOT, "static", "data", "gallery.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
    counts = ", ".join(f"{k}={len(v)}" for k, v in data["pairs"].items())
    print(f"wrote {os.path.relpath(out, ROOT)} ({counts})")


if __name__ == "__main__":
    main()
