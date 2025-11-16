# Production Order

Role: Learning Architect — efficient sequencing derived from `notebook_requirements.md` so downstream contributors can batch assets, reuse scaffolds, and avoid blockers.

## Build Waves and Rationale
| Wave | Days | Theme | Rationale |
| --- | --- | --- | --- |
| 1. Infinity & Calculus Foundations | 01-04 | Set conceptual baseline on infinity, limits, derivatives, integrals | Opens with conceptual hooks that set notation, proof cadence, and visualization conventions reused throughout later days. |
| 2. Linear Algebra Toolkit | 05-08 | Vector spaces through Fourier analysis | Shared plot styles, `numpy`/`matplotlib` utilities, and geometric diagram templates crafted once to serve four notebooks. |
| 3. Rigorous Analysis & Topology | 09-11 | Real analysis, topology, metric spaces | Builds on limit visualizations from Wave 1; epsilon/metric widgets refined here before algebraic structures rely on them. |
| 4. Abstract Algebra to Complex Analysis | 12-15 | Groups, rings/fields, complex numbers/functions | Requires fully vetted symbolic-manipulation snippets, Cayley table generator, and Argand-plane assets; batches all algebra-heavy writing. |
| 5. Differential Equations & Geometry | 16-19 | ODEs, PDEs, manifolds, tensors | Shares simulation scaffolds (heat/cooling) plus 3D plotting utilities across four demanding notebooks. |
| 6. Probability to Fractals Finale | 20-24 | Probability, measure, numerical methods, chaos, fractals | Uses randomness/fractal rendering assets and culminates in spectacle-heavy visuals for closing week. |

## Detailed Sequence Checklist
1. **Wave 1 (Days 01-04)**
   - Deliverables: shared markdown tone guide, diagonalization illustration template, epsilon-delta widget prototype, FTC slider scaffold.
   - Dependency note: epsilon-delta widget required before Day 09; FTC slider informs later integral-based diagnostics.
2. **Wave 2 (Days 05-08)**
   - Deliverables: vector space axiom checker, eigen animation base notebook, Fourier signal sampler.
   - Dependency note: eigen animation reused in Day 07 & Day 08; color palette defined here feeds later diagrams.
3. **Wave 3 (Days 09-11)**
   - Deliverables: eps-delta proof helper, topology visualizer, metric comparison plotting script.
   - Dependency note: metric visualizer informs tensor distance comparisons in Day 19.
4. **Wave 4 (Days 12-15)**
   - Deliverables: Cayley table generator, modular arithmetic sandbox, Argand plane plotter, Cauchy–Riemann grid deformation demo.
   - Dependency note: modular arithmetic sandbox reused by Day 22 error analysis to compare discrete structures vs. numerical approximations.
5. **Wave 5 (Days 16-19)**
   - Deliverables: ODE/PDE solver scaffolds, animation export presets, manifold chart visualizer, tensor transformation helper.
   - Dependency note: animation presets reused for chaos visualizations in Day 23.
6. **Wave 6 (Days 20-24)**
   - Deliverables: probability simulation harness, measure approximation script, numerical method comparison harness, chaos bifurcation plotter, fractal renderer.
   - Dependency note: probability harness informs randomized initial conditions for chaos notebooks; fractal renderer uses color palette from Wave 2.

## Shared Resources to Prepare Before Notebook Authoring
- **`/output/26/assets/holiday_palette.json`** — canonical color set for diagrams (used across all waves). If missing, create once during Wave 2 kickoff.
- **`/output/26/assets/diagram_templates/`** — SVG/PNG bases for ladders, snowfields, igloo maps, Argand plane grid. Populate during Wave 1 & 2.
- **`/output/26/code_snippets/common_imports.py`** — Colab cell with standard imports (`numpy`, `sympy`, `matplotlib`, `scipy`, `ipywidgets`). Finalize during Wave 1 to avoid repeated edits.
- **`/output/26/code_snippets/visualization_utils.py`** — helper functions for plotting styles, animation export (`matplotlib.animation.FuncAnimation` presets). Add after Wave 2 deliverables settle.
- **`/output/26/code_snippets/simulation_utils.py`** — shared solvers for ODE/PDE/probability; stubbed in Wave 5 but referenced early for planning.
- **Reference Library Spreadsheet** — maintain cite list (URL, annotation) for each day while progressing; ensures Engagement Writer can pull consistent blurbs.

## Prerequisites and Blocking Dependencies
| Blocking Item | Needed By | Owner | Status Notes |
| --- | --- | --- | --- |
| Epsilon-Delta interactive widget prototype | Days 02, 09 | Wave 1 dev | Must be validated before Wave 3 starts to prevent rewrite of continuity sections. |
| Vector space diagram style guide | Days 05-08, 18-19 | Wave 2 design | Shared by manifolds/tensors for consistent look. |
| Cayley table generator | Day 12 & references in Day 22 | Wave 4 dev | Without it, algebra notebooks stall; prioritize after topology assets. |
| Animation export presets (MP4/GIF instructions) | Days 08, 17, 19, 23, 24 | Wave 5 engineer | Should be locked before Wave 6 to avoid re-rendering heavy visuals. |
| Fractal renderer baseline notebook | Day 24 (finale) | Wave 6 engineer | Kick off concurrently with Wave 5 testing to leave buffer for render tuning. |

## Execution Notes
- Work in waves sequentially but allow **Wave 6 fractal renderer** to begin asset generation while Wave 5 validation runs (parallelizable GPU tasks).
- After each wave, run a mini retro to verify shared utilities before moving forward; flag issues in `production_order.md` inline notes if status changes.
- Maintain consistent folder naming `dayXX_<slug>`; reserve slugs now (e.g., `day01_infinity`, `day08_fourier`, `day24_fractals`).
