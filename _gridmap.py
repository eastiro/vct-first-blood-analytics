"""Render VLR's Ascent minimap large, with a coordinate grid, for visual zoning."""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from pathlib import Path

BASE = Path(r"D:\好玩的项目\valorant-analytics")
MAP = BASE / "_cache" / "maps" / "vlr_ascent.png"
OUT = BASE / "figures"
OUT.mkdir(exist_ok=True)

img = Image.open(MAP).convert("RGBA")
arr = np.array(img)

fig, ax = plt.subplots(figsize=(14, 14), facecolor="#0e131b")
ax.set_facecolor("#0e131b")
ax.imshow(arr, extent=(0, 1024, 1024, 0))
ax.set_xlim(0, 1024)
ax.set_ylim(1024, 0)
ax.set_xticks(np.arange(0, 1025, 128))
ax.set_yticks(np.arange(0, 1025, 128))
ax.grid(color="#FF4655", alpha=0.35, linewidth=0.7)
ax.tick_params(colors="#e1e7ef", labelsize=9)
for sp in ax.spines.values():
    sp.set_color("#1c2330")
ax.set_title("VLR Ascent minimap — 1024 grid", color="#e1e7ef", fontsize=16, pad=12)

out = OUT / "ascent_grid.png"
fig.savefig(out, dpi=110, facecolor="#0e131b", bbox_inches="tight")
print("saved", out)
