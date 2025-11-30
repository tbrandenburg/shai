## Context
The user needs a well-researched essay describing the scouting movement in Sweden, touching on its history, national organizations, cultural values, outdoor traditions, inclusivity initiatives, and modern relevance while grounding the narrative in credible, citable sources.

## Role Descriptions
### Role: research-analyst
- Agent Path: .github/agents/10-research-analysis/research-analyst.md

### Role: technical-writer
- Agent Path: .github/agents/08-business-product/technical-writer.md

### Role: cultural-editor
- Purpose: Ensure the essay balances historical accuracy with engaging storytelling while maintaining consistent tone and structure
- Focus: Content coherence, factual verification against provided sources, narrative polish, and reader-friendly pacing
- Style: Detail-oriented, culturally sensitive, concise with actionable revision notes
- Note: Custom role defined inline

## Chronologic Task List
- [x] [research-analyst] Compile Swedish scouting research brief — Perform focused desk research on Svenska Scouterna history, key milestones, membership trends, outdoor education practices, and societal impact using authoritative Swedish and international sources; summarize findings with bullet lists, short paragraphs, and source citations saved to `output/47/research_brief.md` so later roles can reference concrete data points.
  * Summary: Compiled multi-source brief on history, membership, outdoor culture, and inclusivity in `output/47/research_brief.md`.
- [x] [technical-writer] Draft essay outline — Read `output/47/research_brief.md`, identify 3–4 narrative pillars (e.g., origins, cultural traditions, modern programs, future challenges), and create a structured outline in `output/47/essay_outline.md` that lists section headings, thesis statement, and supporting evidence notes tied to cited sources.
  * Summary: Produced four-pillar outline with thesis and source-linked evidence notes in `output/47/essay_outline.md`.
- [x] [technical-writer] Write essay draft — Using `output/47/research_brief.md` and `output/47/essay_outline.md`, craft a 900–1,100 word essay saved to `output/47/essay_draft.md` with an engaging introduction, thematic body sections following the outline, cited facts, and a reflective conclusion on Swedish scouting’s relevance today.
  * Summary: Drafted a 1,098-word essay in `output/47/essay_draft.md` translating the outline into a cited narrative on history, outdoor ethos, inclusion, and future relevance.
- [x] [cultural-editor] Review draft and log improvements — Read `output/47/essay_draft.md`, verify facts against `output/47/research_brief.md`, and document clarity, flow, and tone adjustments in `output/47/editorial_feedback.md` with numbered recommendations plus any required rewrites or citation fixes.
  * Summary: Logged five numbered edits—thesis clarity, municipal reach, section transitions, citation coverage, and Jamboree26 emphasis—in `output/47/editorial_feedback.md`.
- [x] [technical-writer] Produce final essay — Incorporate each point from `output/47/editorial_feedback.md`, revise `output/47/essay_draft.md`, and save the polished version as `output/47/final_essay.md` that highlights the adjustments made and ensures citations, word count, and narrative flow meet publication-ready quality.
  * Summary: Recast the thesis, added municipal scale/bridge sentence, tightened Support Fund citations, referenced Jamboree26, and delivered the polished article in `output/47/final_essay.md`.
