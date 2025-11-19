# Feature 1 – Replan Backlog

## Inputs Considered
- QA sign-off (`feature1_qa_signoff.md`): confirms AC pass but flags coverage gaps, limited failure-path automation, and persistence toggles not exercised.
- Error analysis (`feature1_error_analysis.md`): highlights always-on embedding fallback warnings and misleading CLI diagnostics that can trigger false alarms.

## Scope Adjustments
1. **Clarify Diagnostics** – Treat context-only summarization as an intentional mode, not an error; update CLI messaging and telemetry.
2. **Optional Embedding Upgrade Path** – Provide a documented, opt-in dependency group for high-fidelity embeddings so releases can scale beyond the dummy PDF while staying token-free by default.
3. **Test Matrix Expansion** – Add negative-path + performance regression tests to meet QA confidence expectations before GA.

## Prioritized Backlog
| Rank | Priority | Item | Owner | Target Window | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | P0 | Separate `fallback_used` from intentional `llm_backend` selection; emit structured diagnostics fields and update CLI output to "Embedding backend: hash (expected)" vs. true fallbacks. | Backend lead (Alex) | 2 days | Removes constant warning noise and unblocks monitoring rollout.
| 2 | P0 | Reclassify embedding fallback log level based on config (warning only when unexpected) and document behavior in CLI notes/readme. | Backend + Tech Writer (Sam) | 2 days (parallel) | Addresses user confusion noted in error analysis §Observed Symptoms.
| 3 | P1 | Publish `extras = {"embeddings": ["sentence-transformers==..."]}` in `pyproject.toml`, add download toggle in config, and validate both paths. | AI engineer (Priya) | 1 week | Enables parity with LangChain when networked while keeping lightweight default.
| 4 | P1 | Expand automated tests: (a) missing PDF, (b) invalid query, (c) run with `sentence-transformers` extra, (d) persistence toggle scenario. | Test automator (Jordan) | 1 week + aligns with Sprint 18 | Direct QA request to mitigate coverage risk from signoff §Coverage & Metrics.
| 5 | P1 | Add telemetry hooks for cache size/load times and embed fallback flags for ops dashboards. | DevOps (Mina) | 1 week | Prepares monitoring to detect real regressions once released.
| 6 | P2 | Update documentation + onboarding playbook to reflect new extras, diagnostics, and troubleshooting paths; include release notes. | Project manager + Technical Writer | 3 days | Keeps stakeholders and support teams aligned on scope change.
| 7 | P2 | Evaluate persistence toggles + multi-document ingestion performance under larger PDFs; capture benchmarks in QA addendum. | QA + Performance engineer | 1.5 weeks | Addresses QA risk about limited scenarios before next milestone.

## Timeline & Next Steps
- **Immediate (Next 2 days):** Items 1-2 unblock logging/diagnostics noise before further testing.
- **Short Term (Next 1 week):** Items 3-5 handled in parallel tracks (AI, QA/Test, DevOps) with daily sync to manage interdependencies.
- **Mid Term (Within 2 weeks):** Documentation refresh and performance validation (Items 6-7) close the loop ahead of release candidate.

## Ownership & Communication
- Daily triage stand-up led by Project Manager to track backlog burn-down.
- Update risk register once diagnostic fixes release; downgrade "Limited scenario coverage" risk only after Item 4 completes.
- Share progress snapshots with stakeholders every 3 days, emphasizing timeline adherence and scope adjustments above.
