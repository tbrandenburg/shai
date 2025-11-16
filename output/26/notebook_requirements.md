# Notebook Requirements

Generated in the Learning Architect role to consolidate all guidance for the downstream teams. Upstream blueprint, narrative, scaffold, and delivery files were unavailable in the workspace, so the structure below synthesizes the issue brief into a single reference that no later agent needs to augment.

Each day lists the required topic, learning goal, seasonal hook, experiment outline (with suggested libraries), diagram needs, references, and the final hands-on learner task.

### Day 01 — Exploring Infinity: Countable vs. Uncountable Sets
- **Learning Goal**: Differentiate between countable and uncountable sets using mappings and diagonal arguments.
- **Seasonal Hook**: Santa's infinite naughty/nice scrolls versus the never-ending snowfall over the North Pole.
- **Experiment Outline**: Use Python lists to enumerate rationals, then demonstrate Cantor's diagonalization using strings; leverage `itertools` and basic string manipulation.
- **Diagram Requirements**: Side-by-side schematic showing ladders (countable) and snowfield continuum (uncountable) plus a flowchart of the diagonal construction.
- **References**: Cantor's work overview (Khan Academy), Brilliant.org article on countability, "How to Count Infinity" Numberphile video.
- **Final Learner Task**: Write a function that, given a list of binary strings, constructs a new "holiday code" not on the list and explain why it proves uncountability.

### Day 02 — The Beauty of Limits: Understanding Convergence
- **Learning Goal**: Interpret limits graphically and algebraically, including epsilon-delta intuition.
- **Seasonal Hook**: Elves timing Santa's sleigh approaching chimney rooftops ever more closely.
- **Experiment Outline**: Use `sympy` to compute symbolic limits and `matplotlib` to visualize sequences converging to chimney heights.
- **Diagram Requirements**: Annotated plot showing epsilon bands around a limit and sequence terms approaching it.
- **References**: Paul's Online Math Notes (limits), 3Blue1Brown "Introduction to Limits", MIT OCW calculus notes.
- **Final Learner Task**: Create a notebook cell that lets users set epsilon and N, then verifies the epsilon definition for a chosen convergent sequence.

### Day 03 — Derivatives Beyond Slopes: A Deep Dive into Differentiability
- **Learning Goal**: Understand differentiability criteria, corner cases, and higher-order derivatives.
- **Seasonal Hook**: Candy-cane production line monitoring conveyor belt speed and jerk.
- **Experiment Outline**: Use symbolic differentiation (`sympy`) and finite difference approximations to compare smooth vs. cusp functions.
- **Diagram Requirements**: Overlay plot of function and tangent lines at selected points, plus a table comparing derivative estimates.
- **References**: Stewart Calculus differentiability chapter, Khan Academy "Derivatives as Functions", Wolfram MathWorld entry on differentiability.
- **Final Learner Task**: Analyze a custom piecewise "candy cane" function, prove where it fails to be differentiable, and justify with plots.

### Day 04 — Integrals as Areas and More: The Fundamental Theorem of Calculus
- **Learning Goal**: Connect definite integrals with antiderivatives and accumulation functions.
- **Seasonal Hook**: Counting wrapped gifts piled under the tree as area under a "present density" curve.
- **Experiment Outline**: Use numerical integration (`scipy.integrate.quad`) vs. symbolic antiderivatives to show equivalence.
- **Diagram Requirements**: Filled area plot plus accumulation function graph showing increasing total gifts.
- **References**: Essence of Calculus Chapter 7 (YouTube), MIT OCW notes on FTC, Brilliant "Fundamental Theorem" course.
- **Final Learner Task**: Build an interactive slider (via `ipywidgets`) to vary the upper limit of integration and display the accumulating present count.

### Day 05 — Vector Spaces: What Makes a Space Linear?
- **Learning Goal**: Identify axioms of vector spaces and recognize counterexamples.
- **Seasonal Hook**: Modeling sleigh routes as combinations of basis reindeer-flight vectors.
- **Experiment Outline**: Implement checks for closure and axioms on custom Python objects; test spaces of polynomials and holiday light color tuples.
- **Diagram Requirements**: Illustrate vector addition/parallelograms in 2D and 3D with festive colors.
- **References**: Linear Algebra Done Right (ch.1), 3Blue1Brown "Vectors", Khan Academy vector intro.
- **Final Learner Task**: Design a "toy workshop" vector space candidate and prove (or disprove) each axiom explicitly.

### Day 06 — Basis and Dimension: Building Blocks of All Vector Spaces
- **Learning Goal**: Compute bases, show linear independence, and reason about dimension.
- **Seasonal Hook**: Determining minimal ornament styles needed to decorate all trees.
- **Experiment Outline**: Use `numpy.linalg` to find bases via row-reduced echelon form; include a script that transforms spanning sets.
- **Diagram Requirements**: Tree-shaped graphic labeling basis vectors as ornament archetypes.
- **References**: Axler basis chapter, Khan Academy basis/dimension, Gilbert Strang MIT lecture.
- **Final Learner Task**: Given a set of holiday melody vectors, find a basis and explain the dimension with supporting computations.

### Day 07 — Eigenvalues and Eigenvectors: The Language of Transformations
- **Learning Goal**: Explain eigen concepts and compute them for 2×2 and 3×3 matrices.
- **Seasonal Hook**: Crystal snowflakes that stretch uniformly along magical axes.
- **Experiment Outline**: Use `numpy.linalg.eig` and manual characteristic polynomials; animate repeated transformations.
- **Diagram Requirements**: Arrows showing vectors before/after transformation with highlighted eigenvectors.
- **References**: 3Blue1Brown "Essence of Linear Algebra" chapter on eigenvectors, Khan Academy, Strang lecture notes.
- **Final Learner Task**: Analyze a "gift rotation-scaling" matrix, compute eigenpairs, and describe the geometric action in prose.

### Day 08 — Fourier Series: Decomposing Signals into Sines and Cosines
- **Learning Goal**: Understand Fourier coefficients and reconstruct periodic signals.
- **Seasonal Hook**: Decomposing jingle bell melodies into pure tones.
- **Experiment Outline**: Sample a holiday tune waveform, compute coefficients numerically, and visualize partial sums using `numpy` and `matplotlib`.
- **Diagram Requirements**: Plots comparing original vs. reconstructed signals, plus coefficient bar charts.
- **References**: BetterExplained Fourier article, Khan Academy series, MIT 18.03 notes.
- **Final Learner Task**: Record or synthesize a short festive waveform, approximate with first N terms, and evaluate reconstruction quality.

### Day 09 — Introduction to Real Analysis: ε-δ Proofs Made Friendly
- **Learning Goal**: Practice crafting epsilon-delta proofs for limits and continuity.
- **Seasonal Hook**: Ensuring hot cocoa temperature stays within cozy tolerances.
- **Experiment Outline**: Provide helper functions to visualize eps-delta neighborhoods and prompt learners to formalize statements.
- **Diagram Requirements**: Number line showing δ-interval mapped to ε-band on graph.
- **References**: Abbott "Understanding Analysis", ProofWiki epsilon-delta, YouTube Real Analysis by Dr. Trefor Bazett.
- **Final Learner Task**: Complete a structured epsilon-delta proof for a quadratic function with commentary referencing the cocoa metaphor.

### Day 10 — Topology Basics: Open Sets and Continuous Maps
- **Learning Goal**: Define open/closed sets, continuity via preimages, and simple topological spaces.
- **Seasonal Hook**: Mapping cozy neighborhoods within Santa's village using open igloo clusters.
- **Experiment Outline**: Use Python to model topologies on finite sets and check continuity of sample functions.
- **Diagram Requirements**: Stylized village map showing open balls overlapping.
- **References**: Munkres Topology intro, Math Insight topology primer, Visual Topology blog posts.
- **Final Learner Task**: Construct a topology on a 4-point "village" set and justify whether a given mapping is continuous.

### Day 11 — Metric Spaces: Distances in Abstract Worlds
- **Learning Goal**: Explore different metrics, including taxicab and discrete, and verify metric properties.
- **Seasonal Hook**: Reindeer delivering gifts over grids, forests, and teleport pads.
- **Experiment Outline**: Implement functions to verify metric axioms and visualize distance spheres under multiple metrics.
- **Diagram Requirements**: Comparative plots of circles under Euclidean vs. Manhattan metrics.
- **References**: Rudin "Principles of Mathematical Analysis" metric chapter, Khan Academy metric spaces overview, Cut-the-Knot resources.
- **Final Learner Task**: Design a custom "snowflake" metric on R² and prove it satisfies the triangle inequality with a plotted example.

### Day 12 — Group Theory: Symmetries Everywhere
- **Learning Goal**: Understand group axioms, subgroups, and simple permutation groups.
- **Seasonal Hook**: Snowflake symmetries and ornament rotations.
- **Experiment Outline**: Use `sagecell` via `sagemathcell` link or Python permutations to show D6 symmetries; include Cayley table generation.
- **Diagram Requirements**: Snowflake annotated with symmetry operations plus Cayley table heatmap.
- **References**: Gallian "Contemporary Abstract Algebra", Visual Group Theory by Nathan Carter, Group Explorer app documentation.
- **Final Learner Task**: Build the multiplication table for a chosen ornament symmetry group and identify subgroups.

### Day 13 — Rings and Fields: The Algebraic Structures Behind Numbers
- **Learning Goal**: Differentiate rings vs. fields, give examples/non-examples, and explore modular arithmetic.
- **Seasonal Hook**: Magic candy machines operating modulo flavors.
- **Experiment Outline**: Implement modular arithmetic operations, verify field axioms for finite fields, and show where rings fail.
- **Diagram Requirements**: Flow diagram of candy machine operations plus modular clock visualization.
- **References**: Artin Algebra intro, Khan Academy modular arithmetic, Brilliant finite field course.
- **Final Learner Task**: Prove whether Z₁₂ is a field or not and construct a simple field of order 9 using code cells.

### Day 14 — Complex Numbers and the Argand Plane
- **Learning Goal**: Represent complex numbers geometrically, convert between forms, and visualize multiplication.
- **Seasonal Hook**: Polar lights swirling around the North Pole traced as complex vectors.
- **Experiment Outline**: Use `matplotlib` to plot complex numbers, conversions, and rotations; include interactive widgets for modulus/argument.
- **Diagram Requirements**: Argand plane plot with holiday-colored vectors and rotation animations.
- **References**: Visual Complex Analysis (Needham) intro, Khan Academy complex numbers, 3Blue1Brown video "But what is the complex plane?".
- **Final Learner Task**: Build a mini tool where users multiply two complex numbers and describe the geometric effect in writing.

### Day 15 — Complex Functions and the Cauchy–Riemann Equations
- **Learning Goal**: Explain analyticity and verify Cauchy–Riemann equations.
- **Seasonal Hook**: Mapping gingerbread village decorations through magical frosting functions.
- **Experiment Outline**: Symbolically compute partial derivatives and test CR equations using `sympy`; visualize conformal maps on a grid.
- **Diagram Requirements**: Before/after grid showing deformation while preserving angles.
- **References**: Visual Complex Analysis CR chapter, Math Insight articles, Complex Analysis textbook by Stein & Shakarchi.
- **Final Learner Task**: Choose a complex function, verify analyticity, and illustrate how it warps a gingerbread grid.

### Day 16 — Differential Equations: Modeling Change
- **Learning Goal**: Solve first-order ODEs analytically and numerically.
- **Seasonal Hook**: Cooling hot chocolate mugs in snowy weather.
- **Experiment Outline**: Use `scipy.integrate.solve_ivp` and analytic solutions to compare; include residual plots.
- **Diagram Requirements**: Slopes field plus solution curves overlay.
- **References**: Differential Equations in 24 Hours (Zill), Paul's Online Notes ODE section, 3Blue1Brown "Differential equations".
- **Final Learner Task**: Model hot chocolate cooling with chosen parameters and explain deviations between numeric and analytic solutions.

### Day 17 — Partial Differential Equations: Heat, Waves, and Laplace
- **Learning Goal**: Introduce classic PDEs and simple separation-of-variables solutions.
- **Seasonal Hook**: Heat diffusion through gingerbread walls, wave bells ringing.
- **Experiment Outline**: Use finite difference approximations for heat equation via `numpy`; animate temperature map.
- **Diagram Requirements**: Heatmap animation frames plus line plot showing wave solution.
- **References**: MIT 18.303 notes, Khan Academy PDE intro, YouTube visual PDE ("Animated PDEs").
- **Final Learner Task**: Implement a simple 1D heat equation solver for a gingerbread rod and discuss results.

### Day 18 — Manifolds: Curved Spaces in Higher Dimensions
- **Learning Goal**: Describe charts, atlases, and why manifolds generalize surfaces.
- **Seasonal Hook**: Mapping Santa's globe-trotting routes over curved Earth ornaments.
- **Experiment Outline**: Use `sympy` or `numpy` to parametrize sphere and torus surfaces; show local coordinate transformations.
- **Diagram Requirements**: 3D plot of sphere with highlighted patches and coordinate grids.
- **References**: Lee "Introduction to Smooth Manifolds" overview, Brilliant manifold primer, 3Blue1Brown "Manifolds" video snippets.
- **Final Learner Task**: Build a short write-up explaining how two overlapping charts describe part of the sphere using computed transformations.

### Day 19 — Tensor Calculus: The Language of General Relativity
- **Learning Goal**: Understand tensors as multilinear maps and basic index notation.
- **Seasonal Hook**: Reindeer harness forces represented by tensors to keep sleigh balanced.
- **Experiment Outline**: Use `sympy` tensor module to manipulate simple tensors and perform coordinate transformations.
- **Diagram Requirements**: Diagram of sleigh forces with arrows labeled by tensor components.
- **References**: "A Student's Guide to Vectors and Tensors" (Fleisch), Khan Academy relativity tensors, PBS Space Time tensor intro.
- **Final Learner Task**: Implement a transformation of a rank-2 tensor between coordinate systems and interpret the physical meaning for the sleigh.

### Day 20 — Probability Theory: Random Variables and Distributions
- **Learning Goal**: Define discrete/continuous random variables, expectation, and variance.
- **Seasonal Hook**: Random gift assignments and snowfall distributions.
- **Experiment Outline**: Simulate variables with `numpy.random`, plot histograms, and compute expected gifts per child.
- **Diagram Requirements**: Histogram plus cumulative distribution plot.
- **References**: MIT OCW probability notes, Khan Academy probability distributions, Seeing Theory visualizations.
- **Final Learner Task**: Design a custom "gift lottery" distribution, simulate it, and justify fairness criteria.

### Day 21 — Measure Theory: What Is "Size" Really?
- **Learning Goal**: Explain sigma-algebras, measures, and simple measurable sets.
- **Seasonal Hook**: Measuring glitter coverage on wrapping paper of fractal patterns.
- **Experiment Outline**: Use Python to approximate measure of Cantor-like sets via intervals; compare Lebesgue vs. counting.
- **Diagram Requirements**: Visualization of iterative removal in a Cantor set with glitter motif.
- **References**: Terence Tao "An Introduction to Measure Theory" excerpts, Math StackExchange canonical posts, Brilliant measure theory primer.
- **Final Learner Task**: Implement a script approximating the measure of a Cantor dust ornament and explain the limiting value.

### Day 22 — Numerical Methods: Computing the Impossible
- **Learning Goal**: Introduce root finding, numerical integration, and error analysis.
- **Seasonal Hook**: Approximating Santa's optimal delivery schedule when equations get messy.
- **Experiment Outline**: Implement Newton's method, trapezoidal rule, and Monte Carlo estimation in Python, comparing errors.
- **Diagram Requirements**: Convergence plots and error vs. iterations chart with candy-cane color palette.
- **References**: Numerical Recipes intro, Khan Academy numerical analysis, SciPy documentation.
- **Final Learner Task**: Choose a tough equation tied to delivery timing and solve it numerically with error commentary.

### Day 23 — Chaos Theory: When Simple Rules Make Wild Behavior
- **Learning Goal**: Explore logistic map, sensitivity to initial conditions, and strange attractors.
- **Seasonal Hook**: Tracking unpredictable twinkle patterns on synchronized light strings.
- **Experiment Outline**: Iterate logistic map, plot bifurcation diagram, and animate divergence of close starts using `matplotlib`.
- **Diagram Requirements**: Bifurcation plot plus time-series comparison.
- **References**: Strogatz "Nonlinear Dynamics", Veritasium chaos video, Khan Academy chaos intro.
- **Final Learner Task**: Run logistic map experiments for multiple parameters and write observations about chaos in light shows.

### Day 24 — Fractals and Self-Similarity: Beauty in Infinite Detail
- **Learning Goal**: Define fractals, self-similarity, and compute simple fractal dimensions.
- **Seasonal Hook**: Designing ever-branching Christmas tree ornaments.
- **Experiment Outline**: Generate Koch snowflake and Mandelbrot set zooms using `numpy` and `matplotlib`; compute perimeter/area estimates.
- **Diagram Requirements**: High-resolution fractal render with festive palette.
- **References**: The Fractal Geometry of Nature (Mandelbrot), Khan Academy fractals, Coding Train Mandelbrot tutorial.
- **Final Learner Task**: Create a custom fractal ornament (Koch variant or L-system), render it, and explain its self-similarity rule.
