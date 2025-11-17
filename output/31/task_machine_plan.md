## Context
The user needs a current-state mega trend analysis that culminates in both a comprehensive essay and a Reveal.js presentation, so the plan must gather globally relevant evidence, translate it into an accessible narrative, and deliver presentation-ready assets inside `output/31`.

## Role Descriptions
### Role: trend-analyst
- Agent Path: .github/agents/10-research-analysis/trend-analyst.md

### Role: technical-writer
- Agent Path: .github/agents/08-business-product/technical-writer.md

### Role: frontend-developer
- Agent Path: .github/agents/01-core-development/frontend-developer.md

## Chronologic Task List
- [x] [trend-analyst] Map current mega trends — Collect and cite the most recent global trend signals (technology, socio-economic, environmental, geopolitical) plus quantitative indicators, then synthesize at least five validated mega trends with their drivers, timelines, and strategic implications into `output/31/mega_trend_research.md`.
  * Summary: Produced `mega_trend_research.md` detailing five evidenced mega trends with quantitative signals, timelines, and actionable implications for the downstream essay and presentation.
- [x] [technical-writer] Compose mega trend essay — Read `output/31/mega_trend_research.md`, outline the narrative arc, and write a structured 1,200+ word essay saved to `output/31/mega_trend_essay.md` that explains each trend, compares impacts, notes risks/opportunities, and references the cited sources.
  * Summary: Authored a 1,200+ word narrative in `mega_trend_essay.md` weaving all five trends with comparative impacts, risks, opportunities, and source citations.
- [x] [frontend-developer] Build Reveal.js presentation — Read `output/31/mega_trend_essay.md`, distill slide-friendly talking points, and create `output/31/mega_trend_presentation.html` using Reveal.js (CDN-based build) with agenda, per-trend slides, visuals/infographics placeholders, and speaker notes tied back to the essay.
  * Summary: Authored a Reveal.js deck with agenda, dedicated slides for each mega trend, visual placeholders, and speaker notes anchored to `mega_trend_essay.md`.
