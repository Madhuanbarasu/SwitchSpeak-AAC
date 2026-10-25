"""2D plane-strain FEA of the SwitchSpeak base-plate cross-section under an equivalent drop load (scikit-fem).
Case A: flat 2.5 mm floor.  Case B: 3.0 mm floor + two 2x6 mm ribs at the 1/3 points (as in the CAD model).
Run: python3 fea_base_plate.py -> out/fea_results.json, out/fea.png
"""
import json, numpy as np
from skfem import *
from skfem.models.elasticity import linear_elasticity, lame_parameters
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

# --- material: PETG (typical datasheet values, conservative printed yield) ---
E, NU, YIELD = 2100.0, 0.38, 40.0          # MPa
LAM, MU = lame_parameters(E, NU)
# --- drop load ---
H_DROP, STOP, M_SUP, G = 1.0, 0.004, 0.15, 9.81     # drop height m, stopping distance m, mass resting on floor kg
V = np.sqrt(2 * G * H_DROP); A_DEC = V ** 2 / (2 * STOP)
F = M_SUP * A_DEC                                       # N, equivalent static inertial force
PATCH_X, PATCH_LEN = 42.5, 60.0                         # load footprint 60 (along rib) x 40 (across) mm, centred
P = F / (60.0 * 40.0)                                   # MPa over 60 x 40 mm footprint
SPAN, DX = 85.0, 0.5

WALL_T, WALL_H = 2.5, 10.0
def build(t, ribs):
    X0 = -WALL_T
    nx = int((SPAN + 2 * WALL_T) / DX) + 1; ny = int(((max(t + (6 if ribs else 0), WALL_H)) / DX)) + 1
    xs, ys = X0 + np.arange(nx) * DX, np.arange(ny) * DX
    def inside(cx, cy):
        if cx < 0 or cx > SPAN: return cy < WALL_H                    # side walls (stubs) carry the floor to the ground
        if cy < t: return True
        return ribs and any(abs(cx - rc) < 1.0 for rc in (SPAN / 3, 2 * SPAN / 3))
    quads = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            if inside(xs[i] + DX / 2, ys[j] + DX / 2):
                n0 = j * nx + i; quads.append([n0, n0 + 1, n0 + 1 + nx, n0 + nx])
    quads = np.array(quads).T
    used = np.unique(quads); remap = -np.ones(nx * ny, int); remap[used] = np.arange(len(used))
    X, Y = np.meshgrid(xs, ys); pts = np.vstack([X.ravel(), Y.ravel()])[:, used]
    return MeshQuad(pts, remap[quads])

def solve(t, ribs):
    mesh = build(t, ribs); elem = ElementVector(ElementQuad2()); basis = Basis(mesh, elem)
    K = asm(linear_elasticity(LAM, MU), basis)
    fac = mesh.facets_satisfying(lambda x: (np.abs(x[1] - t) < 1e-9) & (x[0] >= PATCH_X - PATCH_LEN / 2) & (x[0] <= PATCH_X + PATCH_LEN / 2))
    fb = FacetBasis(mesh, elem, facets=fac)
    @LinearForm
    def load(v, w): return -P * v.value[1]
    f = asm(load, fb)
    # supports: ground contact under the end walls (3 mm wide) -> vertical restraint; one node fixed horizontally
    sup = basis.get_dofs(lambda x: (np.abs(x[1]) < 1e-9) & ((x[0] <= 1e-9) | (x[0] >= SPAN - 1e-9)))
    fix_x = basis.get_dofs(lambda x: (np.abs(x[1]) < 1e-9) & (np.abs(x[0] + WALL_T) < 1e-9)).nodal['u^1']
    D = np.concatenate([sup.nodal['u^2'], fix_x])
    u = solve_(K, f, D)
    # stresses at element level (average of quadrature points), plane strain with sigma_zz = nu*(sxx+syy)
    gu = basis.interpolate(u).grad                      # shape (2,2,nel,nqp)
    exx, eyy, exy = gu[0, 0], gu[1, 1], 0.5 * (gu[0, 1] + gu[1, 0])
    tr = exx + eyy
    sxx, syy, sxy = 2 * MU * exx + LAM * tr, 2 * MU * eyy + LAM * tr, 2 * MU * exy
    szz = NU * (sxx + syy)
    vm = np.sqrt(0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2) + 3 * sxy ** 2)
    vm_el = vm.mean(axis=1)
    ux, uy = u[basis.nodal_dofs[0]], u[basis.nodal_dofs[1]]
    return mesh, vm_el, float(np.abs(uy).max())

def solve_(K, f, D):
    from skfem.utils import solve as sksolve, condense
    return sksolve(*condense(K, f, D=D))

res = {"load": {"drop_height_m": H_DROP, "impact_speed_ms": round(float(V), 2), "stop_distance_mm": STOP * 1000,
                "decel_g": round(float(A_DEC / G), 0), "supported_mass_kg": M_SUP, "equiv_force_N": round(float(F), 0),
                "pressure_MPa": round(float(P), 3)},
       "material": {"name": "PETG", "E_MPa": E, "nu": NU, "working_yield_MPa": YIELD}}
cases = {"A": (2.5, False, "Iteration 1: flat 2.5 mm floor"), "B": (3.0, True, "Iteration 2: 3.0 mm floor + 2 ribs (2 x 6 mm)"),
         "C": (4.5, True, "Iteration 3: 4.5 mm floor + 2 ribs (final)")}
fig, axes = plt.subplots(3, 1, figsize=(9.2, 6.6))
for ax, (k, (t, ribs, name)) in zip(axes, cases.items()):
    mesh, vm, dmax = solve(t, ribs)
    peak = float(vm.max()); fos = YIELD / peak
    # report peak excluding the 1.5 mm re-entrant corner zone at rib roots (numerical singularity in sharp-corner model)
    cx = mesh.p[:, mesh.t].mean(axis=1)
    mask = np.ones(len(vm), bool)
    for wc in (0.0, SPAN): mask &= ~((np.abs(cx[0] - wc) < 3.0) & (cx[1] < t + 3.0))   # support edge + sharp wall-root corner: numerical singularities (root is filleted 1.5 mm in CAD)
    if ribs:
        for rc in (SPAN / 3, 2 * SPAN / 3): mask &= ~((np.abs(cx[0] - rc) < 2.5) & (cx[1] < t + 1.5))
    peak_s = float(vm[mask].max()); fos_s = YIELD / peak_s
    res[k] = {"name": name, "floor_mm": t, "ribs": ribs, "peak_vm_MPa": round(peak, 1), "peak_vm_excl_corner_MPa": round(peak_s, 1),
              "fos": round(fos, 2), "fos_excl_corner": round(fos_s, 2), "max_deflection_mm": round(dmax, 3), "elements": int(mesh.t.shape[1])}
    polys = [mesh.p[:, mesh.t[:, e]].T for e in range(mesh.t.shape[1])]
    pc = PolyCollection(polys, array=vm, cmap="turbo", clim=(0, YIELD), edgecolors="none"); ax.add_collection(pc)
    ax.set_xlim(-4, SPAN + 4); ax.set_ylim(-1.5, 11.5)
    ax.set_aspect("equal"); ax.set_yticks([]); ax.set_xlabel("") ; ax.set_title(f"{name}:  peak von Mises {peak_s:.1f} MPa, FoS {fos_s:.2f}", fontsize=12.5, loc="left")
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
cb = fig.colorbar(pc, ax=axes, orientation="vertical", fraction=0.02, pad=0.01); cb.set_label("von Mises stress (MPa), red = at PETG working yield", fontsize=11); cb.ax.tick_params(labelsize=11)
axes[2].set_xlabel("Position across the 85 mm floor span (mm)", fontsize=11)
for a in axes: a.tick_params(labelsize=11)
fig.savefig("out/fea.png", dpi=170, bbox_inches="tight"); json.dump(res, open("out/fea_results.json", "w"), indent=2)
print(json.dumps(res, indent=2))
