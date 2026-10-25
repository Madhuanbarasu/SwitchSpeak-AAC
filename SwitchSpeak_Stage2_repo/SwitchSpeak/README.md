# SwitchSpeak: Adaptive, Literacy-Free Single-Switch AAC Device

Vishwakarma Awards 2026-27, Stage 2. Application ID: VK26-IITI-AS-0173
Theme 2: Assistive Solutions | Sub-theme: AAC Hardware

## What is in this repository
| Folder | Contents | How to reproduce |
|---|---|---|
| `cad/` | Parametric enclosure model (CadQuery), STEP assembly, STL per part | `pip install cadquery trimesh` then `python3 cad_switchspeak.py` and `python3 render_cad.py` |
| `fea/` | 2D plane-strain FEA of the base floor (scikit-fem), results and plot | `pip install scikit-fem` then `python3 fea_base_plate.py` |
| `sim/` | Adaptive scan-order simulation (30 seeds x 6,000 selections) and results | `python3 sim_adaptive.py` |
| `schematic/` | Net-level schematic script and image (ESP32, TFT, microSD, I2S amp, RTC, power) | `python3 schematic.py` |
| `renders/` | Isometric and exploded CAD renders | produced by `cad/render_cad.py` |

## Status (honest)
- Stage 2 so far is design-stage work: CAD, floor-plate FEA, schematic and the adaptive-ordering simulation.
- The simulation and FEA are models, not measurements. Simulation: 12 symbols, 1.5 s per scan step, Zipf-skewed usage, 4 time-of-day contexts.
- FEA is a 2D slice with a conservative equivalent drop load; 3D FEA on the final CAD is planned.
- BOM prices and lead times are indicative estimates. The hardware prototype is built in Stage 2 Month 1 onward; build photos will be added here.

## Key results
- Selection time: fixed order 9.97 s, usage-adaptive 7.45 s (-25%), adaptive + context 6.74 s (-32%); 0.6 symbols re-ordered per selection.
- Floor FoS under a 1 m drop load (PETG, 40 MPa working yield): flat 2.5 mm 0.95, 3.0 mm + ribs 1.36, final 4.5 mm + ribs 2.84.
