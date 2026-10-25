import numpy as np, trimesh, math
from PIL import Image, ImageDraw, ImageFont

COL = {"base_shell": "#2f6fa8", "lid": "#5aa6e0", "pcb": "#1b7f4f", "esp32_devkit": "#2b2b2b", "tft_pcb": "#b5282d",
       "tft_glass": "#101830", "speaker": "#505866", "battery_holder": "#d7a021", "li_ion_18650": "#8a4cc4",
       "switch_housing": "#3d5a80", "switch_cap_tpu": "#f08a2a"}
LABEL = {"lid": "Lid (PETG)", "speaker": "40 mm speaker", "tft_pcb": "2.4 in TFT module", "esp32_devkit": "ESP32 dev board",
         "pcb": "Main PCB / perfboard", "li_ion_18650": "18650 Li-ion cell", "battery_holder": "Battery holder",
         "base_shell": "Base shell + ribs (PETG)", "switch_cap_tpu": "Soft TPU switch cap", "switch_housing": "Switch housing"}
SW_XY = (118, -2)

def hexrgb(h): h = h.lstrip("#"); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)

def load(offsets, lid_on=True):
    items = []
    for i, (name, c) in enumerate(COL.items()):
        m = trimesh.load(f"out/{name}.stl")
        v = m.vertices.copy(); dz = offsets.get(name, 0.0)
        v[:, 2] += dz
        if name.startswith("switch"): v[:, 0] += SW_XY[0]; v[:, 1] += SW_XY[1]
        items.append((name, v, m.faces, i, hexrgb(c)))
    return items

def render(items, az=-52, el=28, W=1800, H=1100, ss=2, margin=0.08):
    az, el = math.radians(az), math.radians(el)
    d = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
    r = np.cross([0, 0, 1], d); r /= np.linalg.norm(r); u = np.cross(d, r)
    allv = np.vstack([v for _, v, _, _, _ in items])
    sx, sy = allv @ r, allv @ u
    w0, h0 = sx.max() - sx.min(), sy.max() - sy.min()
    scale = min(W * ss * (1 - 2 * margin) / w0, H * ss * (1 - 2 * margin) / h0)
    cx, cy = (sx.max() + sx.min()) / 2, (sy.max() + sy.min()) / 2
    Wp, Hp = W * ss, H * ss
    img = np.full((Hp, Wp, 3), 255, float); zb = np.full((Hp, Wp), -1e9); idb = np.full((Hp, Wp), -1, int)
    light = np.array([-0.45, -0.35, 0.82]); light /= np.linalg.norm(light)
    proj = {}
    for name, v, f, pid, base in items:
        p = np.stack([(v @ r - cx) * scale + Wp / 2, Hp / 2 - (v @ u - cy) * scale, v @ d], 1)
        proj[name] = p
        tri = v[f]; n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        ln = np.linalg.norm(n, axis=1); ok = ln > 1e-9; n[ok] /= ln[ok, None]
        vis = (n @ d) > 0
        shade = 0.38 + 0.62 * np.clip(n @ light, 0, 1) + 0.12 * np.clip(n @ np.array([0.6, -0.6, 0.1]), 0, 1)
        for k in np.nonzero(vis & ok)[0]:
            a, b, c = p[f[k]]
            x0, x1 = int(max(min(a[0], b[0], c[0]), 0)), int(min(max(a[0], b[0], c[0]) + 1, Wp - 1))
            y0, y1 = int(max(min(a[1], b[1], c[1]), 0)), int(min(max(a[1], b[1], c[1]) + 1, Hp - 1))
            if x1 <= x0 or y1 <= y0: continue
            den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            if abs(den) < 1e-9: continue
            xs, ys = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
            l1 = ((b[1] - c[1]) * (xs - c[0]) + (c[0] - b[0]) * (ys - c[1])) / den
            l2 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / den
            l3 = 1 - l1 - l2
            m = (l1 >= -1e-4) & (l2 >= -1e-4) & (l3 >= -1e-4)
            if not m.any(): continue
            z = l1 * a[2] + l2 * b[2] + l3 * c[2]
            sub = zb[y0:y1, x0:x1]; upd = m & (z > sub)
            if not upd.any(): continue
            sub[upd] = z[upd]; idb[y0:y1, x0:x1][upd] = pid
            img[y0:y1, x0:x1][upd] = np.clip(base * shade[k], 0, 255)
    # outlines where part id or depth jumps
    edge = np.zeros((Hp, Wp), bool)
    for dy, dx in ((0, 1), (1, 0)):
        a1 = idb[:Hp - dy, :Wp - dx]; a2 = idb[dy:, dx:]
        z1 = zb[:Hp - dy, :Wp - dx]; z2 = zb[dy:, dx:]
        e = (a1 != a2) | (np.abs(z1 - z2) > 4.0)
        edge[:Hp - dy, :Wp - dx] |= e
    img[edge] = img[edge] * 0.35
    out = Image.fromarray(img.astype(np.uint8)).resize((W, H), Image.LANCZOS)
    def to_px(name, pt3):
        v = np.array(pt3, float)
        return ((v @ r - cx) * scale + Wp / 2) / ss, (Hp / 2 - (v @ u - cy) * scale) / ss
    return out, to_px

def font(sz, bold=False):
    for p in (f"/usr/share/fonts/opentype/inter/Inter-{'Bold' if bold else 'Regular'}.otf",):
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()

# ---- assembled isometric ----
items = load({"lid": 22})
img, _ = render(items, W=1600, H=900)
img.save("out/cad_iso.png"); print("iso done")

# ---- exploded ----
off = {"battery_holder": 8, "pcb": 16, "li_ion_18650": 34, "esp32_devkit": 38, "tft_pcb": 56, "tft_glass": 56, "speaker": 56, "lid": 94,
       "switch_cap_tpu": 36}
items = load(off)
img, to_px = render(items, W=2000, H=1250, margin=0.16)
d = ImageDraw.Draw(img); F = font(36, True)
anch = {"lid": (-60, 30, 104), "speaker": (48, -19, 68), "tft_pcb": (-32, -8, 86), "esp32_devkit": (-20, 8, 55),
        "pcb": (-45, 30, 26), "li_ion_18650": (30, -30, 56), "battery_holder": (45, -30, 25), "base_shell": (-70, -10, 14),
        "switch_cap_tpu": (SW_XY[0], SW_XY[1] + 20, 62), "switch_housing": (SW_XY[0] + 20, SW_XY[1] - 30, 10)}
left = ["lid", "tft_pcb", "esp32_devkit", "pcb", "base_shell"]; right = ["speaker", "li_ion_18650", "battery_holder", "switch_cap_tpu", "switch_housing"]
for side, names in (("L", left), ("R", right)):
    for i, nm in enumerate(names):
        px = to_px(nm, anch[nm]); ty = 90 + i * 225
        tx = 30 if side == "L" else 1970
        tw = d.textlength(LABEL[nm], font=F)
        lx = tx + tw + 12 if side == "L" else tx - tw - 12
        d.line([(lx, ty + 22), px], fill=(70, 80, 100), width=3); d.ellipse([px[0] - 5, px[1] - 5, px[0] + 5, px[1] + 5], fill=(70, 80, 100))
        d.text((tx if side == "L" else tx - tw, ty), LABEL[nm], font=F, fill=(30, 41, 80))
img.save("out/cad_exploded.png"); print("exploded done")
