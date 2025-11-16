# Remediation Plan

## Objective
Design a concrete sequence of actions that closes the gaps highlighted in `protection_insights.md` and `status_report.md`, ensuring `main` cannot accept unvetted code and secrets are continuously scanned.

## Assumptions
- Org administrators can edit protection rules and enable GitHub Advanced Security (GHAS).
- The repository uses GitHub Actions for CI and already has at least one workflow that should be required.

## Step-by-Step Plan
1. **Enumerate current protections** (Owner: Repo Admin; Tooling: GitHub UI/API)
   - Capture a full export or screenshots of the existing branch protection configuration for `main`, including required reviews, status checks, and push rules.
   - Share the evidence with the security team so subsequent changes are auditable.

2. **Define mandatory CI checks** (Owner: DevOps Lead; Tooling: GitHub Actions, workflow_dispatch tests)
   - Identify the minimal CI workflows that must pass before merging (e.g., `build-and-test`, `security-scan`).
   - Run each workflow manually to confirm they are currently green and produce deterministic results.

3. **Enforce required status checks** (Owner: Repo Admin; Tooling: Branch protection UI or `gh api repos/:owner/:repo/branches/main/protection`)
   - Enable required status checks for the workflows selected in Step 2 and set enforcement to "Require branches to be up to date".
   - Block force pushes and deletions to `main` to prevent bypassing the checks.

4. **Enable secret scanning + push protection** (Owner: Org Security Admin; Tooling: GitHub Advanced Security settings)
   - Verify GHAS licensing and enable secret scanning and push protection on the organization, then ensure `tbrandenburg/shai` is opted in.
   - Configure alert routing so the security team receives notifications for any detected secrets.

5. **Validate reviewer and provenance policies** (Owner: Repo Maintainer; Tooling: Branch protection UI + org policy docs)
   - Set the minimum number of required reviewers (≥1) and enable "Require review from Code Owners" if applicable.
   - Turn on "Require signed commits" or enforce a GPG/Sigstore equivalent if your supply-chain policy mandates provenance.

6. **Document and monitor** (Owner: Security Analyst; Tooling: `output/25` reports, issue tracker)
   - Record the updated settings, link to GitHub audit logs, and raise follow-up tickets for any exceptions.
   - Schedule quarterly reviews to ensure protections remain intact and CI coverage evolves with the codebase.
