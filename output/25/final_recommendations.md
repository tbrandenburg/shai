# Final Recommendations Checklist

Every mitigation below ties back to the risks captured in `protection_insights.md` and reaffirmed in `status_report.md`; implementation guidance references `remediation_plan.md` steps.

- [ ] **Gate merges on required CI** — Require the `build-and-test` and `security-scan` workflows (or successors) on `main`, set "Require branches to be up to date," and block force pushes so no code ships without automated validation. *Reference: protection_insights.md (status checks off), remediation_plan.md Steps 2–3.*
- [ ] **Enable GHAS secret scanning + push protection** — Confirm licensing, toggle both features at the org level, and route alerts to the security distro to close the blind spot on credential leakage. *Reference: protection_insights.md (secret scanning unknown), remediation_plan.md Step 4.*
- [ ] **Lock reviewer & provenance policies** — Capture admin evidence of branch rules, require ≥1 reviewer plus Code Owners, disable bypasses, and enforce signed commits (or Sigstore) for supply-chain integrity. *Reference: protection_insights.md (reviewer/signature data unavailable), remediation_plan.md Step 5.*
- [ ] **Document and monitor** — Store screenshots/API exports, log updates in the tracker, and schedule quarterly reviews so regressions surface quickly. *Reference: status_report.md (controls unclear), remediation_plan.md Step 6.*
