"""SwitchSpeak wiring schematic (net-level, net labels join same-named nets). Run: python3 schematic.py -> out/schematic.png"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch

fig, ax = plt.subplots(figsize=(20.5, 10.6)); ax.set_xlim(0, 200); ax.set_ylim(0, 113); ax.axis("off")
NAVY, GREY = "#1E3A8A", "#334155"
NET = {"VBAT": "#B45309", "3V3": "#B91C1C", "GND": "#111827", "SW_IN": "#0F766E", "SW_BACKUP": "#0F766E", "VBAT_SENSE": "#7C2D12"}
FS, FT = 13, 15

def box(x, y, w, h, title, fc="#F8FAFC", title_in=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2", fc=fc, ec=NAVY, lw=1.6))
    if title_in: ax.text(x + w / 2, y + h - 1.0, title, ha="center", va="top", fontsize=FT - 1, fontweight="bold", color=NAVY)
    else: ax.text(x + w / 2, y + h + 1.0, title, ha="center", va="bottom", fontsize=FT, fontweight="bold", color=NAVY)

def line(pts, c=GREY, lw=1.5):
    xs, ys = zip(*pts); ax.plot(xs, ys, color=c, lw=lw, solid_capstyle="round")
def dot(x, y, c=GREY): ax.plot(x, y, "o", color=c, ms=5)
def txt(x, y, t, ha="left", c=GREY, fs=FS, fw="normal"): ax.text(x, y, t, ha=ha, va="center", fontsize=fs, color=c, fontweight=fw)

def netflag(x, y, name, side="R", stub=3.5):
    c = NET.get(name, GREY)
    if side == "R": line([(x, y), (x + stub, y)], c); txt(x + stub + 0.5, y, name, c=c, fw="bold")
    else: line([(x - stub, y), (x, y)], c); txt(x - stub - 0.5, y, name, ha="right", c=c, fw="bold")

# =============== ESP32 ===============
EX0, EX1, EY0, EY1 = 88, 128, 44, 101
box(EX0, EY0, EX1 - EX0, EY1 - EY0, "ESP32-WROOM-32E dev board", fc="#DBEAFE")
for n, y, net in [("3V3", 96, "3V3"), ("GND", 92, "GND"), ("GPIO4", 72, "SW_IN"), ("GPIO13", 67, "SW_BACKUP"), ("GPIO34 (ADC)", 62, "VBAT_SENSE")]:
    txt(EX0 + 1.2, y, n, fw="bold", c=NAVY); netflag(EX0, y, net, "L")
right = [("GPIO18  SCK", 92, "SCK"), ("GPIO23  MOSI", 88, "MOSI"), ("GPIO19  MISO", 84, "MISO"), ("GPIO5   TFT_CS", 80, "TFT_CS"),
         ("GPIO2   TFT_DC", 76, "TFT_DC"), ("GPIO16  TFT_RST", 72, "TFT_RST"), ("GPIO17  SD_CS", 68, "SD_CS"),
         ("GPIO26  I2S_BCLK", 64, "BCLK"), ("GPIO25  I2S_LRC", 60, "LRC"), ("GPIO27  I2S_DIN", 56, "DIN"),
         ("GPIO21  I2C_SDA", 52, "SDA"), ("GPIO22  I2C_SCL", 48, "SCL")]
for n, y, k in right:
    txt(EX1 - 1.2, y, n, ha="right", fw="bold", c=NAVY); line([(EX1, y), (EX1 + 3, y)])

# =============== right-hand modules ===============
MX = 168
mods = {
 "TFT": ("2.4 in TFT (ILI9341, SPI)", 82.5, 109.5, [("VCC", 108, "3V3"), ("GND", 105, "GND"), ("CS", 102, "TFT_CS"), ("RESET", 99, "TFT_RST"), ("DC/RS", 96, "TFT_DC"),
          ("SDI (MOSI)", 93, "MOSI"), ("SCK", 90, "SCK"), ("LED", 87, "LED3V3"), ("SDO (MISO)", 84, "MISO")]),
 "SD": ("microSD module (SPI)", 59.5, 77.5, [("CS", 76, "SD_CS"), ("SCK", 73, "SCK"), ("MOSI", 70, "MOSI"), ("MISO", 67, "MISO"), ("VCC", 64, "3V3"), ("GND", 61, "GND")]),
 "AMP": ("MAX98357A I2S amp", 36.5, 54.5, [("BCLK", 53, "BCLK"), ("LRC", 50, "LRC"), ("DIN", 47, "DIN"), ("VIN", 44, "VBAT"), ("GND", 41, "GND"), ("SD", 38, "VBAT")]),
 "RTC": ("DS3231 RTC (I2C)", 19.5, 31.5, [("SDA", 30, "SDA"), ("SCL", 27, "SCL"), ("VCC", 24, "3V3"), ("GND", 21, "GND")]),
}
pin_y = {}
for key, (title, y0, y1, pins) in mods.items():
    box(MX, y0, 22, y1 - y0, title)
    for pn, y, net in pins:
        line([(MX - 3, y), (MX, y)]); txt(MX + 1.0, y, pn)
        pin_y.setdefault(net, []).append(y)
        if net in NET:
            c = NET[net]; line([(MX - 9, y), (MX - 3, y)], c); txt(MX - 9.4, y, net, ha="right", c=c, fs=FS - 1.5, fw="bold")
        if net == "LED3V3":
            c = NET["3V3"]; line([(MX - 11, y), (MX - 3, y)], c); ax.add_patch(Rectangle((MX - 8.5, y - 0.9), 3.2, 1.8, fc="white", ec=GREY, lw=1.2))
            txt(MX - 11.4, y, "3V3", ha="right", c=c, fs=FS - 1.5, fw="bold"); txt(MX - 7.0, y + 2.1, "100 Ω", ha="center", fs=FS - 2.5)
# speaker
line([(MX + 22, 44.5), (MX + 25, 44.5)]); line([(MX + 22, 47.5), (MX + 25, 47.5)])
ax.add_patch(Rectangle((MX + 25, 43.0), 10, 6.0, fc="#F1F5F9", ec=GREY, lw=1.4)); txt(MX + 30, 46.0, "3 W 4 Ω\nspeaker", ha="center", fs=FS - 1.8)
txt(MX + 22.5, 51.2, "OUT+ / OUT−", fs=FS - 2.3)

# signal channels
sig_order = ["SCK", "MOSI", "MISO", "TFT_CS", "TFT_DC", "TFT_RST", "SD_CS", "BCLK", "LRC", "DIN", "SDA", "SCL"]
palette = ["#0284C7", "#7C3AED", "#DB2777", "#EA580C", "#CA8A04", "#16A34A", "#0D9488", "#2563EB", "#9333EA", "#C026D3", "#E11D48", "#65A30D"]
esp_y = {k: y for _, y, k in right}; chan0 = 133.0
for i, s in enumerate(sig_order):
    cx = chan0 + i * 2.6; col = palette[i]; ys = list(pin_y[s])
    line([(EX1 + 3, esp_y[s]), (cx, esp_y[s])], col)
    line([(cx, min(ys + [esp_y[s]])), (cx, max(ys + [esp_y[s]]))], col)
    for y in ys: line([(cx, y), (MX - 3, y)], col)
    dot(cx, esp_y[s], col)
    if len(ys) > 1: [dot(cx, y, col) for y in ys]

# =============== power / input blocks (left, net-label style) ===============
box(2, 100, 18, 11, "USB-C 5 V")
txt(3.5, 108, "VBUS"); txt(3.5, 103, "GND")
box(27, 100, 24, 11, "TP4056 charger + protection")
txt(28.5, 108, "IN+"); txt(28.5, 103, "IN−")
line([(20, 108), (27, 108)], NET["3V3"]); line([(20, 103), (27, 103)], NET["GND"])
txt(49.5, 108, "B+", ha="right"); netflag(51, 108, "VBAT"); txt(49.5, 103, "B−", ha="right"); netflag(51, 103, "GND")
box(27, 82, 24, 11, "18650 Li-ion (3.0–4.2 V)")
txt(49.5, 90, "+", ha="right", c=NET["3V3"], fw="bold"); netflag(51, 90, "VBAT")
txt(49.5, 85, "−", ha="right", c=NET["GND"], fw="bold"); netflag(51, 85, "GND")
box(27, 62, 24, 14, "AP2112K-3.3 LDO")
txt(28.5, 73, "3.3 V, 600 mA", fs=FS - 1.5)
txt(49.5, 73, "IN", ha="right"); netflag(51, 73, "VBAT")
txt(49.5, 69, "OUT", ha="right"); netflag(51, 69, "3V3")
txt(49.5, 65, "GND", ha="right"); netflag(51, 65, "GND")
box(27, 43, 24, 14, "Battery sense")
txt(28.5, 52.5, "100 kΩ / 100 kΩ\ndivider", fs=FS - 1.5, ha="left")
txt(49.5, 55, "top", ha="right", fs=FS - 1.5); netflag(51, 55, "VBAT")
txt(49.5, 51, "mid", ha="right", fs=FS - 1.5); netflag(51, 51, "VBAT_SENSE")
txt(49.5, 46, "bottom", ha="right", fs=FS - 1.5); netflag(51, 46, "GND")
box(27, 17, 24, 22, "Switch input")
txt(28.5, 31.5, "J1 3.5 mm jack tip\n→ 1 kΩ → SW_IN\n100 nF: SW_IN to GND\nJ1 sleeve → GND", fs=FS - 1.8)
txt(49.5, 21.2, "SW2 tactile (backup)", ha="right", fs=FS - 2.6)
txt(49.5, 37, "SW_IN", ha="right", fs=FS - 1.2); netflag(51, 37, "SW_IN")
netflag(51, 22.5, "SW_BACKUP"); netflag(51, 19, "GND")

ax.set_ylim(10, 113)
fig.savefig("out/schematic.png", dpi=170, bbox_inches="tight", facecolor="white"); print("ok")
