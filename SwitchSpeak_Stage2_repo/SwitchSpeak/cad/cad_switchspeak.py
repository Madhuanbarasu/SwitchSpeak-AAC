"""SwitchSpeak enclosure: parametric CadQuery model (units: mm).
Run: python3 cad_switchspeak.py -> writes out/*.stl and out/switchspeak_assembly.step
"""
import cadquery as cq, math, os
os.makedirs("out", exist_ok=True)

# ---- parameters ----
L, W = 140.0, 90.0          # outer length, width
HB, HL = 22.0, 10.0         # base height, lid height
WALL, FLOOR = 2.5, 4.5      # wall, floor thickness (floor raised 2.5 -> 3.0 -> 4.5 mm after FEA iterations)
R = 8.0                     # vertical corner radius
RIB_W, RIB_H = 2.0, 6.0     # floor stiffening ribs
INNER_W = W - 2 * WALL

def rounded_box(l, w, h, r):
    return cq.Workplane("XY").box(l, w, h, centered=(True, True, False)).edges("|Z").fillet(r)

# ---- 1. base shell ----
base = rounded_box(L, W, HB, R).faces("<Z").edges().fillet(2.0)
cavity = rounded_box(L - 2 * WALL, W - 2 * WALL, HB, R - WALL).faces("<Z").edges().fillet(1.5).translate((0, 0, FLOOR))   # 1.5 mm floor-wall fillet
base = base.cut(cavity)
for y in (-INNER_W / 6, INNER_W / 6):                       # two ribs at 1/3 points of the floor span
    base = base.union(cq.Workplane("XY").box(L - 2 * WALL - 2, RIB_W, RIB_H, centered=(True, True, False)).translate((0, y, FLOOR)))
for sx in (-1, 1):                                          # screw bosses
    for sy in (-1, 1):
        boss = cq.Workplane("XY").circle(3.5).extrude(HB - FLOOR).translate((sx * 60, sy * 35, FLOOR))
        base = base.union(boss).cut(cq.Workplane("XY").circle(1.25).extrude(12).translate((sx * 60, sy * 35, HB - 12)))
for (y, wd, ht, z) in ((20, 6.2, 6.2, 11), (-10, 9.2, 3.4, 11)):   # 3.5 mm jack (switch input) and USB-C (charging)
    base = base.cut(cq.Workplane("XY").box(8, wd, ht).translate((L / 2 - 1.5, y, z)))
for sx, sy in ((-1, -1), (1, -1)):                          # rubber feet recesses
    base = base.cut(cq.Workplane("XY").circle(6).extrude(1.0).translate((sx * 55, sy * 32, 0)))

# ---- 2. lid ----
lid = rounded_box(L, W, HL, R).faces(">Z").edges().fillet(2.0)
lid = lid.cut(rounded_box(L - 2 * WALL, W - 2 * WALL, HL - WALL, R - WALL))
lid = lid.cut(cq.Workplane("XY").box(50, 38, 10).translate((-22, 0, HL)))          # display window
grille = cq.Workplane("XY")
pts = [(48 + dx, dy) for dx in (-12, -6, 0, 6, 12) for dy in (-12, -6, 0, 6, 12) if math.hypot(dx, dy) <= 14]
lid = lid.cut(cq.Workplane("XY").pushPoints(pts).circle(1.3).extrude(10).translate((0, 0, HL - 4)))   # speaker grille
for sx in (-1, 1):
    for sy in (-1, 1):
        lid = lid.cut(cq.Workplane("XY").circle(1.7).extrude(12).translate((sx * 60, sy * 35, 0)))

# ---- 3. internal parts (simplified solids) ----
def box(l, w, h, x, y, z): return cq.Workplane("XY").box(l, w, h, centered=(True, True, False)).translate((x, y, z))
pcb_z = FLOOR + RIB_H
pcb = box(70, 50, 1.6, -20, 8, pcb_z)
esp32 = box(51, 28, 6, -20, 8, pcb_z + 1.6)
tft_pcb = box(71.4, 52.2, 1.6, -22, 0, HB + HL - WALL - 4)
tft_glass = box(60, 44, 2.4, -22, 0, HB + HL - WALL - 2.4)
speaker = cq.Workplane("XY").circle(20).extrude(11).translate((48, 0, HB + HL - WALL - 11))
holder = box(78, 21, 17, 10, -30, FLOOR)
cell = cq.Workplane("YZ").circle(9.3).extrude(65).translate((-22.5 + 10 - 10 + 0, -30, FLOOR + 9)).translate((-10, 0, 0)).translate((10, 0, 0))
cell = cq.Workplane("YZ").circle(9.3).extrude(65).translate((10 - 32.5, -30, FLOOR + 9.2))
# ---- 4. external switch (finger / chin / knee press) ----
sw_body = cq.Workplane("XY").circle(34).extrude(18).faces(">Z").edges().fillet(5).translate((0, 0, 0))
sw_body = sw_body.faces(">Z").workplane().circle(26).cutBlind(-3)
sw_cap = cq.Workplane("XY").circle(26).extrude(9).faces(">Z").edges().fillet(7).translate((0, 0, 18))   # soft TPU dome

parts = {
    "base_shell": (base, "#2f6fa8"), "lid": (lid, "#4f9bd6"), "pcb": (pcb, "#1b7f4f"), "esp32_devkit": (esp32, "#222222"),
    "tft_pcb": (tft_pcb, "#b5282d"), "tft_glass": (tft_glass, "#0b1020"), "speaker": (speaker, "#444b55"),
    "battery_holder": (holder, "#d7a021"), "li_ion_18650": (cell, "#7a3db0"),
    "switch_housing": (sw_body, "#3d5a80"), "switch_cap_tpu": (sw_cap, "#e07a1f"),
}
if __name__ == "__main__":
    asm = cq.Assembly(name="SwitchSpeak")
    for name, (wp, col) in parts.items():
        cq.exporters.export(wp, f"out/{name}.stl", tolerance=0.1, angularTolerance=0.2)
        asm.add(wp, name=name, color=cq.Color(col))
    asm.save("out/switchspeak_assembly.step")
    bb = base.val().BoundingBox()
    print("parts:", len(parts), "base bbox", round(bb.xlen,1), round(bb.ylen,1), round(bb.zlen,1))
    vol = sum(wp.val().Volume() for n,(wp,c) in parts.items() if n in ("base_shell","lid"))
    print("shell volume cm3", round(vol/1000,1), "PETG mass g", round(vol/1000*1.27,1))
