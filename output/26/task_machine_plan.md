## Context
Create a festive 24-day Jupyter notebook calendar for a 13-year-old learner, delivering one Colab-ready notebook per day that blends advanced math topics with playful Christmas storytelling, engaging experiments, diagrams, references, and a closing task for each notebook.

## Role Descriptions
### Role: Concept Curator
Purpose: distill the requested topics into a structured learning arc that balances difficulty with excitement. Focus: coverage accuracy, pacing across 24 days, clarity of objectives. Style: concise outlines anchored in pedagogy and seasonal motifs.

### Role: Story Weaver
Purpose: craft narratives, gossip-style anecdotes, and friendly explanations around each topic. Focus: tone, accessibility for a motivated teen, hooks that keep the holiday spirit alive. Style: imaginative yet informative prose with clear calls to action.

### Role: Notebook Engineer
Purpose: transform outlines and narratives into runnable Google Colab notebooks with experiments, diagrams, and references. Focus: technical correctness, reproducibility, consistent structure across 24 files. Style: precise instructions, well-commented code cells, and practical guidance.

## Chronologic Task List
- [x] [Concept Curator] Build Advent blueprint — Read `output/26/issue_conversation.md`, list all 24 topics with target learning goals, seasonal hooks, experiment ideas, and end-of-notebook task prompts; save the structured outline to `output/26/notebook_blueprint.md`.
  * Summary: Created `notebook_blueprint.md` with 24 day-by-day goals, festive hooks, experiments, and closing tasks ready for downstream agents.
- [x] [Story Weaver] Draft narrative modules — Use `output/26/notebook_blueprint.md` to expand each day into story beats, friendly explanations, gossip snippets, and reference pointers; write the detailed narratives to `output/26/narrative_modules.md` with clear per-day subsections.
  * Summary: Crafted per-day narratives with hooks, teen-friendly prose, and references inside `narrative_modules.md`.
- [x] [Notebook Engineer] Define Colab scaffolds — Consult both `output/26/notebook_blueprint.md` and `output/26/narrative_modules.md` to specify the cell order, code/markdown mix, visualization libraries, and experiment setup for each notebook; document the per-day scaffolding guide in `output/26/colab_scaffolds.md`.
  * Summary: Prepared `colab_scaffolds.md` with 24 detailed cell-flow guides, tool choices, and experiment cues ready for notebook assembly.
- [x] [Notebook Engineer] Produce delivery checklist — Review `output/26/colab_scaffolds.md` and outline the concrete steps to instantiate 24 runnable notebooks (including filenames, shared assets, and verification steps); record the final execution checklist in `output/26/calendar_delivery_plan.md` so future agents can build the notebooks without rereading prior documents.
  * Summary: Documented `calendar_delivery_plan.md` with naming schema, shared assets, and verification workflow so notebook builders can proceed without revisiting upstream files.
