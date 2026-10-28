"""Verify the two plant-site markers and dump a labelled reference map."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

BASE = Path(r"D:\好玩的项目\valorant-analytics")
MAP = BASE / "_cache" / "maps" / "vlr_ascent.png"
OUT = BASE / "figures"

# confirmed by zooming: (208, 294) is a diamond = plant site.
# (685, 803) is a square marker in the bottom area - candidate second site.
S1 = (208, 294)
S2 = (685, 803)


def main() -> None:
    img = Image.open(MAP).convert("RGBA")
    bg = Image.new("RGBA", img.size, (14, 19, 27, 255))
    bg.alpha_composite(img)
    arr = np.array(bg)

    fig, ax = plt.subplots(figsize=(13, 13), facecolor="#0e131b")
    ax.set_facecolor("#0e131b")
    ax.imshow(arr, extent=(0, 1024, 1024, 0))
    ax.set_xlim(0, 1024)
    ax.set_ylim(1024, 0)
    ax.grid(color="#FF4655", alpha=0.22, linewidth=0.6)
    ax.set_xticks(np.arange(0, 1025, 128))
    ax.set_yticks(np.arange(0, 1025, 128))
    ax.tick_params(colors="#e1e7ef", labelsize=8)
    for sp in ax.spines.values():
        sp.set_color("#1c2330")

    for (x, y), lab, col in ((S1, "site marker 1", "#FF4655"),
                             (S2, "site marker 2", "#4DA3FF")):
        ax.plot(x, y, "o", ms=16, mfc="none", mec=col, mew=2.5)
        ax.annotate(lab, (x, y), textcoords="offset points", xytext=(14, -14),
                    color=col, fontsize=11)

    ax.set_title("Ascent (VLR minimap) — confirmed plant markers",
                 color="#e1e7ef", fontsize=15, pad=12)
    out = OUT / "ascent_sites_marked.png"
    fig.savefig(out, dpi=110, facecolor="#0e131b", bbox_inches="tight")
    print("saved", out)


if __name__ == "__main__":
    main()
