# Colab Scaffolds — Festive Advent Calendar

Each entry below outlines the Google Colab-ready structure for one day. Follow the listed cell order, keep markdown narration lively, and reuse the specified libraries/visual styles to maintain consistency across the 24-part calendar.

## Day 1 — Exploring Infinity: Countable vs. Uncountable Sets
- **Cell order:** (1) Markdown cover + story hook. (2) Markdown learning goals & recap. (3) Code cell importing `numpy`, `itertools`, `pandas`, `matplotlib`. (4) Markdown walkthrough of finite vs. infinite sets. (5) Code enumerating natural numbers and rationals with tables. (6) Markdown explaining diagonal argument steps. (7) Code cell simulating random real samples and highlighting "missing" numbers. (8) Markdown closing reflection + call-to-action prompt.
- **Code/Markdown mix:** 5 Markdown / 3 Code; emphasize narrative lead-ins around each computation.
- **Libraries & assets:** `numpy`, `itertools`, `pandas`, `matplotlib`, `random`.
- **Experiment setup:** Create helper that maps rationals via `itertools.product`, visualize sample coverage vs. random floating draws, then invite learner to describe why the real list fails.

## Day 2 — The Beauty of Limits: Understanding Convergence
- **Cell order:** Title markdown, objectives markdown, code imports (`numpy`, `matplotlib`, `ipywidgets`), markdown epsilon-delta story, code slider visualizing approaches to a limit, markdown explaining tolerances, code verifying convergence numerically, markdown end task instructions.
- **Code/Markdown mix:** 4 Markdown / 3 Code with an interactive widget cell.
- **Libraries & assets:** `numpy`, `matplotlib`, `ipywidgets`.
- **Experiment setup:** Build `interactive_limit_plot(func, L)` widget allowing epsilon/interval sliders so learners observe when sequences stay in tolerance bands.

## Day 3 — Derivatives Beyond Slopes: A Deep Dive into Differentiability
- **Cell order:** Markdown hook about sleigh checkpoints, markdown learning recap, code imports (`sympy`, `numpy`, `matplotlib`), code defining piecewise functions + symbolic derivative, markdown interpretation of smooth vs. kinked points, code plotting derivatives and highlighting non-differentiable locations, markdown closing task.
- **Code/Markdown mix:** 4 Markdown / 3 Code.
- **Libraries & assets:** `sympy`, `numpy`, `matplotlib`.
- **Experiment setup:** Provide `sympy.Piecewise` example and automated derivative/plot pipeline showing where derivative fails.

## Day 4 — Integrals as Areas and More: Fundamental Theorem of Calculus
- **Cell order:** Markdown narrative, markdown objectives, code imports (`numpy`, `sympy`, `matplotlib`, `scipy.integrate`), code defining snowfall rate, code computing definite integral numerically + symbolically, markdown explaining FTC parts, markdown end task.
- **Code/Markdown mix:** 4 Markdown / 3 Code.
- **Libraries & assets:** `numpy`, `sympy`, `matplotlib`, `scipy.integrate`.
- **Experiment setup:** Compare trapezoidal numerical totals and symbolic antiderivative inside a table; visualize accumulation curve.

## Day 5 — Vector Spaces: What Makes a Space Linear?
- **Cell order:** Markdown choir story, markdown goals, code imports (`numpy`, `pandas`), code implementing vector space axiom checker, markdown debrief, code applying checker to sample light sequences, markdown challenge prompt.
- **Code/Markdown mix:** 3 Markdown / 3 Code.
- **Libraries & assets:** `numpy`, `pandas`.
- **Experiment setup:** Provide `check_axioms(structure)` function and dataset of blinking patterns; show pass/fail per axiom.

## Day 6 — Basis and Dimension: Building Blocks
- **Cell order:** Markdown ornament analogy, markdown objectives, code imports (`numpy`, `sympy`), code performing row reduction for basis, markdown discussing coordinates, code converting decoration vectors into coordinates, markdown wrap-up.
- **Code/Markdown mix:** 4 Markdown / 3 Code.
- **Libraries & assets:** `numpy`, `sympy`.
- **Experiment setup:** Provide matrix of ornament intensities; use `sympy.Matrix.rank()` and `.rref()` to derive basis and coordinate representations.

## Day 7 — Eigenvalues and Eigenvectors
- **Cell order:** Markdown hook, markdown quick theory recap, code imports (`numpy`, `matplotlib`), code building transformation matrix and computing eigenpairs, code plotting original vs. transformed snowflake points, markdown explaining eigen directions, markdown closing task.
- **Code/Markdown mix:** 4 Markdown / 3 Code.
- **Libraries & assets:** `numpy`, `matplotlib`.
- **Experiment setup:** Use polygon snowflake array, show repeated transformation effect, highlight stable axes.

## Day 8 — Fourier Series: Decomposing Signals
- **Cell order:** Markdown recording booth tale, markdown objectives, code imports (`numpy`, `scipy.fft`, `matplotlib`), code loading or generating festive waveform, code computing Fourier coefficients, code plotting reconstruction + coefficient magnitudes, markdown analysis + task.
- **Code/Markdown mix:** 3 Markdown / 4 Code.
- **Libraries & assets:** `numpy`, `scipy.fft`, `matplotlib`, optional `soundfile` for audio snippet.
- **Experiment setup:** Provide helper to truncate series and compare original vs. partial sums; show Gibbs phenomenon discussion.

## Day 9 — Real Analysis: ε-δ Proofs
- **Cell order:** Markdown inspection story, markdown unpacking epsilon/delta, code imports (`sympy`, `ipywidgets`), code widget exploring intervals, markdown bridging to proof structure, code scaffolding template for formal proof (string formatting), markdown closing instructions.
- **Code/Markdown mix:** 4 Markdown / 3 Code with interactive cell.
- **Libraries & assets:** `sympy`, `ipywidgets`.
- **Experiment setup:** Use slider to set epsilon and display required delta for linear function; provide proof skeleton to fill.

## Day 10 — Topology Basics
- **Cell order:** Markdown village map story, markdown key definitions, code imports (`numpy`, `matplotlib`), code visualizing open balls/clopen sets, markdown interpreting visuals, markdown challenge.
- **Code/Markdown mix:** 4 Markdown / 2 Code.
- **Libraries & assets:** `numpy`, `matplotlib` (contourf), optional `networkx` for map graph.
- **Experiment setup:** Plot points with open/closed distinctions under Euclidean vs. taxicab metrics using contour regions.

## Day 11 — Metric Spaces
- **Cell order:** Markdown race narrative, markdown metric axioms summary, code imports (`numpy`, `pandas`, `matplotlib`), code implementing different metrics, code heatmap comparison, markdown story analysis, markdown custom metric task.
- **Code/Markdown mix:** 4 Markdown / 3 Code.
- **Libraries & assets:** `numpy`, `pandas`, `matplotlib`, `seaborn`.
- **Experiment setup:** Provide grid of coordinates and compute distances per metric; render side-by-side heatmaps.

## Day 12 — Group Theory: Symmetries Everywhere
- **Cell order:** Markdown symmetry tale, markdown group definitions, code imports (`sympy`, `itertools`), code constructing dihedral group operations, code generating Cayley table snippet, markdown interpretation + task.
- **Code/Markdown mix:** 3 Markdown / 3 Code.
- **Libraries & assets:** `sympy`, `itertools`, optional `pandas` for tables.
- **Experiment setup:** Build rotation/flip operations dictionary and output table for ornament symmetries.

## Day 13 — Rings and Fields
- **Cell order:** Markdown modular clock story, markdown definition recap, code imports (`numpy`, `pandas`), code building addition/multiplication tables mod n, markdown analyzing inverses, code boolean function for is_field, markdown challenge prompt.
- **Code/Markdown mix:** 4 Markdown / 3 Code.
- **Libraries & assets:** `numpy`, `pandas`.
- **Experiment setup:** Provide interactive `n` selector (optional `ipywidgets`) to test different mod systems.

## Day 14 — Complex Numbers and Argand Plane
- **Cell order:** Markdown spiral rink story, markdown objective list, code imports (`numpy`, `plotly.express`), code function to convert rectangular ↔ polar, code interactive Argand plot, markdown explanation + task instructions.
- **Code/Markdown mix:** 3 Markdown / 3 Code.
- **Libraries & assets:** `numpy`, `plotly`, optional `ipywidgets` for slider rotation.
- **Experiment setup:** Visualize points and show animation for multiplication by unit complex numbers.

## Day 15 — Complex Functions & Cauchy–Riemann
- **Cell order:** Markdown wrapping machine tale, markdown CR intuition, code imports (`sympy`, `plotly.graph_objects`), code checking CR conditions for sample functions, code visualizing grid deformation, markdown reflection + task.
- **Code/Markdown mix:** 4 Markdown / 3 Code.
- **Libraries & assets:** `sympy`, `numpy`, `plotly`.
- **Experiment setup:** Provide helper `check_cr(f)` returning partial derivatives; animate mapping of square grid.

## Day 16 — Differential Equations
- **Cell order:** Markdown cocoa story, markdown explanation of ODE types, code imports (`sympy`, `numpy`, `matplotlib`), code solving analytic ODE via `sympy.dsolve`, code implementing Euler approximation, code plotting both solutions, markdown comparison + closing task.
- **Code/Markdown mix:** 3 Markdown / 4 Code.
- **Libraries & assets:** `sympy`, `numpy`, `matplotlib`, optional `pandas` for tables.
- **Experiment setup:** Provide changeable parameters for cooling constant and compare errors.

## Day 17 — Partial Differential Equations
- **Cell order:** Markdown stocking heat tale, markdown PDE overview, code imports (`numpy`, `matplotlib`, `matplotlib.animation`), code setting up finite-difference grid, code iterating heat equation, code visualizing frames, markdown boundary condition explanation + task.
- **Code/Markdown mix:** 3 Markdown / 4 Code.
- **Libraries & assets:** `numpy`, `matplotlib`, `matplotlib.animation`.
- **Experiment setup:** Use simple explicit scheme with adjustable boundary temperatures; encourage learners to tweak Toe conditions.

## Day 18 — Manifolds
- **Cell order:** Markdown atlas story, markdown objectives, code imports (`numpy`, `plotly`), code generating sphere/torus meshes, code highlighting overlapping coordinate patches, markdown explanation, markdown call-to-action.
- **Code/Markdown mix:** 4 Markdown / 3 Code.
- **Libraries & assets:** `numpy`, `plotly`.
- **Experiment setup:** Display charts with coordinate coloring and explain local-to-global transitions.

## Day 19 — Tensor Calculus
- **Cell order:** Markdown harness narrative, markdown tensor primer, code imports (`numpy`), code building basic tensors (2nd-order) and performing contractions via `numpy.einsum`, code visualizing force components (bar chart), markdown interpretation + task instructions.
- **Code/Markdown mix:** 3 Markdown / 3 Code.
- **Libraries & assets:** `numpy`, `matplotlib` for component plots.
- **Experiment setup:** Provide stress tensor example and compute traction vectors for sleigh direction choices.

## Day 20 — Probability Theory
- **Cell order:** Markdown gift mystery hook, markdown definitions, code imports (`numpy`, `pandas`, `matplotlib`), code sampling discrete distribution + visualization, code computing expectation/variance, markdown interpreting randomness, markdown task prompt.
- **Code/Markdown mix:** 4 Markdown / 3 Code.
- **Libraries & assets:** `numpy`, `pandas`, `matplotlib`, optional `seaborn`.
- **Experiment setup:** Provide dataset of gift probabilities and show Monte Carlo vs. analytical metrics.

## Day 21 — Measure Theory
- **Cell order:** Markdown crumb catastrophe story, markdown sigma-algebra explanation, code imports (`numpy`, `matplotlib`), code pixel-count approximation for irregular shape, markdown discussing measurable sets, markdown Cantor set explanation + task.
- **Code/Markdown mix:** 4 Markdown / 2 Code.
- **Libraries & assets:** `numpy`, `matplotlib`, optional `PIL` for image masks.
- **Experiment setup:** Use binary image to approximate area and segue into Cantor set visualization.

## Day 22 — Numerical Methods
- **Cell order:** Markdown ladder tale, markdown overview of Newton + trapezoidal rules, code imports (`numpy`, `matplotlib`), code implementing Newton iteration with logging, code computing trapezoidal integral, code comparing errors, markdown discussion + prompt.
- **Code/Markdown mix:** 3 Markdown / 4 Code.
- **Libraries & assets:** `numpy`, `matplotlib`, optional `pandas` for tables.
- **Experiment setup:** Provide holly-leaf function definition and show convergence history + error plots.

## Day 23 — Chaos Theory
- **Cell order:** Markdown fairy light chaos story, markdown logistic map background, code imports (`numpy`, `matplotlib`), code generating logistic map iterations, code plotting timeseries and bifurcation diagram, markdown interpreting sensitivity, markdown closing task.
- **Code/Markdown mix:** 4 Markdown / 3 Code.
- **Libraries & assets:** `numpy`, `matplotlib`.
- **Experiment setup:** Include slider/parameters for `r` via `ipywidgets` (optional) and highlight thresholds.

## Day 24 — Fractals and Self-Similarity
- **Cell order:** Markdown final celebration, markdown fractal recap, code imports (`numpy`, `matplotlib`, `plotly`), code rendering Mandelbrot set, code generating snowflake-like L-system fractal, markdown gallery captions, markdown end task instructions.
- **Code/Markdown mix:** 4 Markdown / 3 Code.
- **Libraries & assets:** `numpy`, `matplotlib`, `plotly`, optional `PIL` for saving images.
- **Experiment setup:** Provide helper functions for Mandelbrot zooms and encourage learners to snapshot favorite frames for the gallery.
