# Notebook Blueprint — Festive 24-Day Calendar

Each day blends rigorous math ideas with cheerful seasonal framing, ensuring every notebook guides the learner with goals, experiments, and a culminating task.

## Day 1 — Exploring Infinity: Countable vs. Uncountable Sets
- **Learning goals:** Differentiate countable and uncountable sets; understand diagonal arguments; connect to real numbers.
- **Seasonal hook:** Santa's list grows beyond numbers—can he list every wish?
- **Experiment idea:** Use Python to enumerate rational numbers vs. random sampling of reals.
- **End task:** Write a short explanation proving why the reals cannot be listed like gifts.

## Day 2 — The Beauty of Limits: Understanding Convergence
- **Learning goals:** Interpret limits numerically and graphically; relate epsilon-delta intuition.
- **Seasonal hook:** Approaching Christmas Eve as days shrink—what does "almost there" mean mathematically?
- **Experiment idea:** Interactive slider to approximate limits of given functions in Colab.
- **End task:** Craft an epsilon-style argument showing a provided sequence converges.

## Day 3 — Derivatives Beyond Slopes: A Deep Dive into Differentiability
- **Learning goals:** Revisit derivative definition; explore non-differentiable points; contextualize in physics.
- **Seasonal hook:** Sleigh speed checkpoints where snowdrifts create kinks in the path.
- **Experiment idea:** Symbolic differentiation plus graphing corners/cusps via matplotlib.
- **End task:** Analyze a piecewise function and mark intervals of differentiability with justification.

## Day 4 — Integrals as Areas and More: The Fundamental Theorem of Calculus
- **Learning goals:** Link antiderivatives to accumulation; practice FTC applications.
- **Seasonal hook:** Measuring snowfall depth built up over time along the village road.
- **Experiment idea:** Numeric integration vs. analytic antiderivative comparison using `scipy.integrate`.
- **End task:** Compute the snowfall total from a rate function and explain both FTC parts.

## Day 5 — Vector Spaces: What Makes a Space Linear?
- **Learning goals:** Define vector spaces; test axioms; explore examples beyond geometry.
- **Seasonal hook:** Carol harmonies as vectors combining melodies.
- **Experiment idea:** Build a checklist function to validate whether given structures form vector spaces.
- **End task:** Determine if a set of holiday light sequences forms a vector space and justify.

## Day 6 — Basis and Dimension: Building Blocks of All Vector Spaces
- **Learning goals:** Identify bases; compute dimension; relate to coordinate changes.
- **Seasonal hook:** Choosing minimal ornament sets that generate any tree decoration pattern.
- **Experiment idea:** Perform row-reduction to find bases in Python.
- **End task:** Produce coordinates of decorative patterns relative to a chosen basis.

## Day 7 — Eigenvalues and Eigenvectors: The Language of Transformations
- **Learning goals:** Compute eigenpairs; interpret geometrically; apply to iterated transformations.
- **Seasonal hook:** Magic snowflake machine stretching patterns along special axes.
- **Experiment idea:** Use `numpy.linalg.eig` to analyze festive transformation matrices.
- **End task:** Explain how a transformation affects a snowflake vector using its eigen-decomposition.

## Day 8 — Fourier Series: Decomposing Signals into Sines and Cosines
- **Learning goals:** Understand periodic functions; compute coefficients; reconstruct signals.
- **Seasonal hook:** Breaking down jingle bells sounds into pure tones.
- **Experiment idea:** Sample a recorded jingle waveform and approximate via truncated Fourier series.
- **End task:** Present coefficient plots and discuss convergence behavior for a given festive waveform.

## Day 9 — Introduction to Real Analysis: ε-δ Proofs Made Friendly
- **Learning goals:** Translate informal limit reasoning into epsilon-delta proofs.
- **Seasonal hook:** Guarding Santa's workshop with precision thresholds for toy quality.
- **Experiment idea:** Interactive epsilon-delta visual using widgets showing shrinking intervals.
- **End task:** Complete an epsilon-delta proof for a provided linear function limit.

## Day 10 — Topology Basics: Open Sets and Continuous Maps
- **Learning goals:** Define open/closed sets; understand continuity via pre-images; examine simple topologies.
- **Seasonal hook:** Village map zones with cozy open neighborhoods.
- **Experiment idea:** Visualize open balls in different metrics using contour plots.
- **End task:** Determine whether a sample function is continuous under alternative metrics and justify.

## Day 11 — Metric Spaces: Distances in Abstract Worlds
- **Learning goals:** Explore metric definitions; compare Euclidean, taxicab, discrete metrics.
- **Seasonal hook:** Reindeer race routes scored by different "distance" judges.
- **Experiment idea:** Plot distance heatmaps for multiple metrics over the same grid.
- **End task:** Design a custom "gift-delivery" metric and verify the metric axioms.

## Day 12 — Group Theory: Symmetries Everywhere
- **Learning goals:** Understand group axioms; work with permutation and symmetry groups.
- **Seasonal hook:** Rotational symmetries of snowflake ornaments.
- **Experiment idea:** Use `sympy` to manipulate permutation groups.
- **End task:** Describe the symmetry group of a holiday ornament and list its Cayley table snippet.

## Day 13 — Rings and Fields: The Algebraic Structures Behind Numbers
- **Learning goals:** Distinguish rings vs. fields; explore modular arithmetic.
- **Seasonal hook:** Toy factory clock arithmetic for scheduling elves.
- **Experiment idea:** Implement modular multiplication tables highlighting inverses.
- **End task:** Determine whether a given structure (e.g., integers mod 12) is a field and defend answer.

## Day 14 — Complex Numbers and the Argand Plane
- **Learning goals:** Plot complex numbers; interpret modulus/argument; perform operations.
- **Seasonal hook:** Polar light spirals mapping complex plane points.
- **Experiment idea:** Interactive Argand plotting with `plotly` for rotating ornaments.
- **End task:** Produce a brief guide showing how to convert given complex numbers into polar form.

## Day 15 — Complex Functions and the Cauchy–Riemann Equations
- **Learning goals:** Define complex differentiability; apply CR equations; visualize mappings.
- **Seasonal hook:** Magical wrapping paper patterns transformed via complex maps.
- **Experiment idea:** Map grid deformation demos for functions like z^2 and e^z.
- **End task:** Check CR conditions for a custom festive function and interpret the result.

## Day 16 — Differential Equations: Modeling Change
- **Learning goals:** Solve first-order ODEs; interpret real-world processes.
- **Seasonal hook:** Cooling cocoa modeled by differential equations.
- **Experiment idea:** Use `sympy.dsolve` and Euler method coding for the cocoa model.
- **End task:** Compare analytic and numeric solutions for a gift-delivery rate equation.

## Day 17 — Partial Differential Equations: Heat, Waves, and Laplace
- **Learning goals:** Recognize heat/wave/Laplace equations; understand boundary conditions.
- **Seasonal hook:** Fireplace warmth spreading through a cabin wall.
- **Experiment idea:** Finite-difference simulation of a heated metal stocking.
- **End task:** Explain boundary conditions required to keep stocking toe warm in the simulation.

## Day 18 — Manifolds: Curved Spaces in Higher Dimensions
- **Learning goals:** Intuitively define manifolds; examine charts and atlases; relate to spheres.
- **Seasonal hook:** Mapping Santa's globe-hopping paths as curved surfaces.
- **Experiment idea:** Use `plotly` to visualize spheres and tori with coordinate patches.
- **End task:** Describe local coordinates for a toy track shaped like a torus.

## Day 19 — Tensor Calculus: The Language of General Relativity
- **Learning goals:** Understand tensors as multilinear maps; explore index notation basics.
- **Seasonal hook:** Reindeer hauling tensors representing force components.
- **Experiment idea:** Demonstrate simple tensor contractions using `numpy.einsum`.
- **End task:** Compute a stress tensor contraction relevant to sleigh dynamics.

## Day 20 — Probability Theory: Random Variables and Distributions
- **Learning goals:** Define random variables; work with expectation/variance; compare distributions.
- **Seasonal hook:** Guessing surprise gifts using probability clues.
- **Experiment idea:** Simulate gift draws and plot histograms vs. theoretical PDFs.
- **End task:** Analyze a discrete distribution describing gift outcomes and compute key stats.

## Day 21 — Measure Theory: What Is “Size” Really?
- **Learning goals:** Introduce sigma-algebras; Lebesgue measure intuition; measurable sets.
- **Seasonal hook:** Measuring messy cookie crumbs that don't fit simple shapes.
- **Experiment idea:** Approximate area of irregular gingerbread shapes via pixel counting.
- **End task:** Explain why the Cantor set has zero Lebesgue measure despite infinite points.

## Day 22 — Numerical Methods: Computing the Impossible
- **Learning goals:** Explore root finding, numerical integration, error analysis.
- **Seasonal hook:** Approximating star heights for tree-topping using iterative refinements.
- **Experiment idea:** Implement Newton's method and trapezoidal integration for festive problems.
- **End task:** Compare errors between methods on a provided holly-leaf function.

## Day 23 — Chaos Theory: When Simple Rules Make Wild Behavior
- **Learning goals:** Understand logistic map dynamics; sensitivity to initial conditions.
- **Seasonal hook:** Unruly fairy lights flickering unpredictably.
- **Experiment idea:** Iterate logistic map and create bifurcation diagrams in matplotlib.
- **End task:** Summarize observations about chaos thresholds for different parameter values.

## Day 24 — Fractals and Self-Similarity: Beauty in Infinite Detail
- **Learning goals:** Define fractals; explore Mandelbrot/Julia sets; discuss self-similarity.
- **Seasonal hook:** Zooming into snowflake crystals revealing endless detail.
- **Experiment idea:** Render Mandelbrot and snowflake-like fractals with interactive controls.
- **End task:** Create a mini-gallery of fractal images and explain their recursive rule.
