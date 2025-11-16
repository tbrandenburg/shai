# Calendar Delivery Plan — Notebook Engineer Playbook

## Objective and Inputs
- Transform the approved blueprint (`notebook_blueprint.md`), story treatments (`narrative_modules.md`), and per-day scaffolds (`colab_scaffolds.md`) into 24 runnable Google Colab notebooks.
- Deliverables: 24 `.ipynb` files plus supporting assets stored under `output/26/notebooks/`.
- Success criteria: each notebook launches in Colab without missing imports, follows its scaffold order, and ends with the specified learner task.

## Workspace Preparation
1. **Create directories**
   - `output/26/notebooks/DayXX/` folders (01–24) for notebooks.
   - `output/26/notebooks/shared_assets/` for reusable data, audio clips, meshes, and helper scripts.
2. **Provision shared helpers**
   - `helpers.py`: plotting styles, widget builders, logging utilities referenced by multiple days.
   - `style.css`: optional HTML styling for consistent markdown banners (load via `%%html`).
3. **Record dependency manifest**
   - Maintain `requirements.txt` (Colab auto-installs via first cell) listing superset of libraries mentioned in scaffolds (`numpy`, `sympy`, `pandas`, `matplotlib`, `plotly`, `ipywidgets`, `scipy`, `seaborn`, `itertools`, `sympy`, etc.).
4. **Seed sample datasets** in `shared_assets/` (CSV for probability day, waveform `.npy` for Fourier day, meshes `.json` for manifolds, etc.). Reference them via relative paths.

## Standard Notebook Template (apply then customize per day)
1. Markdown cover (title, festive hook, objective bullets, asset credits).
2. Setup code cell: `%pip install -q -r https://raw.githubusercontent.com/.../requirements.txt` (or inline list) + common imports + `%matplotlib inline` + Plotly renderer setup.
3. Narrative markdown referencing the day's story beats (import from `narrative_modules.md`).
4. Experiment/code/markdown cells exactly in the order prescribed within the specific `colab_scaffolds.md` entry; copy-paste skeleton comments from blueprint and adjust variable names.
5. Reflection markdown concluding with the closing task prompt and a "🎄 Next" pointer.

## Production Loop (repeat for each notebook)
1. **Select day entry** in scaffolds → extract title, libraries, experiment instructions.
2. **Duplicate base template** into `output/26/notebooks/DayXX/DayXX_<slug>.ipynb`.
3. **Edit metadata**: update notebook title, description, author tag, and Colab badge link.
4. **Fill markdown cells** with the matching narrative module text, adapting pronouns/examples for continuity.
5. **Implement code cells** using scaffold details:
   - Import required libraries (include `helpers.py` when relevant).
   - Build data/visualization pipelines exactly as described, referencing shared assets.
   - Comment complex logic for teen readability.
6. **Embed experiments**: add sliders (`ipywidgets`), animations, or tables specified for the day.
7. **Insert closing task** markdown quoting the blueprint's end-of-day challenge and referencing any outputs needed.
8. **Version control**: export `.ipynb` plus optional `.py` text export via `jupyter nbconvert --to script` for diff-friendly review.

## Day-by-Day Roadmap
| Day | Notebook Filename | Primary Libraries & Assets | Experiment Focus |
| --- | --- | --- | --- |
| 01 | `Day01_Infinity_Countability.ipynb` | `numpy`, `itertools`, `pandas`, `matplotlib` | Enumerate rationals, simulate missing reals, diagonalization reflection |
| 02 | `Day02_Limit_Adventures.ipynb` | `numpy`, `matplotlib`, `ipywidgets` | Adjustable epsilon/interval sliders with convergence verifier |
| 03 | `Day03_Differentiability_Quest.ipynb` | `sympy`, `numpy`, `matplotlib` | Piecewise derivative analyzer + kink detector |
| 04 | `Day04_Integral_Magic.ipynb` | `numpy`, `sympy`, `matplotlib`, `scipy.integrate` | Compare snowfall integrals numeric vs. symbolic |
| 05 | `Day05_Vector_Space_Carols.ipynb` | `numpy`, `pandas` | Vector space axiom checker on light patterns |
| 06 | `Day06_Basis_Builder.ipynb` | `numpy`, `sympy` | RREF-based basis finder with ornament coordinates |
| 07 | `Day07_Eigen_Sleigh.ipynb` | `numpy`, `matplotlib` | Snowflake transformation visualizer |
| 08 | `Day08_Fourier_Fanfare.ipynb` | `numpy`, `scipy.fft`, `matplotlib`, optional `soundfile` | Waveform decomposition + reconstruction sliders |
| 09 | `Day09_Epsilon_Delta.ipynb` | `sympy`, `ipywidgets` | Interactive epsilon/delta explorer plus proof scaffold |
| 10 | `Day10_Topology_Town.ipynb` | `numpy`, `matplotlib`, optional `networkx` | Visualize open balls under multiple metrics |
| 11 | `Day11_Metric_Relay.ipynb` | `numpy`, `pandas`, `matplotlib`, `seaborn` | Distance heatmaps comparison |
| 12 | `Day12_Symmetry_Snowdance.ipynb` | `sympy`, `itertools`, `pandas` | Dihedral Cayley table builder |
| 13 | `Day13_Rings_Fields.ipynb` | `numpy`, `pandas`, optional `ipywidgets` | Modular addition/multiplication tables + is_field tester |
| 14 | `Day14_Argand_Aurora.ipynb` | `numpy`, `plotly`, optional `ipywidgets` | Complex plane explorer with animations |
| 15 | `Day15_CauchyRiemann_Wrap.ipynb` | `sympy`, `numpy`, `plotly.graph_objects` | CR checker + grid deformation visual |
| 16 | `Day16_Cocoa_ODEs.ipynb` | `sympy`, `numpy`, `matplotlib`, optional `pandas` | Analytic vs. Euler ODE solver comparison |
| 17 | `Day17_Stocking_PDEs.ipynb` | `numpy`, `matplotlib`, `matplotlib.animation` | Heat equation finite-difference simulation |
| 18 | `Day18_Manifold_Map.ipynb` | `numpy`, `plotly` | Sphere/torus chart overlays |
| 19 | `Day19_Tensor_Trek.ipynb` | `numpy`, `matplotlib` | Tensor contraction + traction visual |
| 20 | `Day20_Gift_Probability.ipynb` | `numpy`, `pandas`, `matplotlib`, `seaborn` | Monte Carlo vs. analytical stats |
| 21 | `Day21_Crumb_Measure.ipynb` | `numpy`, `matplotlib`, `PIL` (optional) | Pixel-based area estimate + Cantor set reflection |
| 22 | `Day22_Numerical_Workshop.ipynb` | `numpy`, `matplotlib`, `pandas` | Newton iteration logger + trapezoid integrator |
| 23 | `Day23_Chaos_Lights.ipynb` | `numpy`, `matplotlib`, optional `ipywidgets` | Logistic map iterations and bifurcation |
| 24 | `Day24_Fractal_Finale.ipynb` | `numpy`, `matplotlib`, `plotly`, `PIL` | Mandelbrot + L-system gallery |

## Shared Asset Details
- `shared_assets/waveforms/choir_wave.npy` — Day 8 audio sample.
- `shared_assets/meshes/sphere_torus.json` — Day 18 surfaces reused in Day 24 fractal comparisons.
- `shared_assets/images/cookie_mask.png` — Day 21 pixel area base.
- `shared_assets/data/gift_probs.csv` — Day 20 distribution table.
- `shared_assets/scripts/logistic_utils.py` — logistic map helpers for Day 23.
(Expand this list as new reusable resources appear; prefer referencing assets rather than redefining in every notebook.)

## Verification Protocol
1. **Static checks**
   - Ensure metadata: `nbformat` 4, Python 3 runtime, Colab badge set, `%pip install` cell present when non-standard libs required.
   - Validate paths: run `python -m json.tool` on notebooks (via nbformat) to confirm integrity.
2. **Runtime tests**
   - In Colab, execute `Runtime > Run all` for each notebook; confirm there are no errors, widget outputs display, and animations render at least one frame.
   - Confirm closing markdown shows the end-of-day task referencing produced artifacts.
3. **Content QA**
   - Spot-check alignment with blueprint: objectives, experiments, and closing tasks must match the curated outline.
   - Verify tone: friendly teen voice, seasonal motifs, and gossip snippets included per narrative module.
4. **Delivery pack-up**
   - Export `.ipynb` files plus optional `.html` previews for quick QA.
   - Update `calendar_delivery_plan.md` status table with completion notes if desired.
   - Produce `README_delivery.md` summarizing access instructions for educators/parents (optional but recommended).

## Handoff Notes
- Keep a change log (dates, decisions, deviations) so future agents can trace adjustments without rereading all scaffolds.
- When assets or helper functions change, update both `helpers.py` and at least one sample notebook before propagating edits across the set.
- Maintain consistent color palettes and typography (e.g., Matplotlib `plt.style.use("Solarize_Light2")` + Plotly template `plotly_dark`) for visual cohesion.
