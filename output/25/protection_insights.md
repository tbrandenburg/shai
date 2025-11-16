# Protection Insights

- **High risk – Status checks unenforced:** `main` reports `required_status_checks.enforcement_level: off`, so Pull Requests can merge without CI or review validation. Require CI checks and disallow direct merges until they pass.
- **High risk – Secret scanning visibility absent:** No `security_and_analysis` data and all secret-scanning endpoints return 403, implying Advanced Security (secret scanning + push protection) is disabled or unobservable. Org admin must confirm the feature state and enable organization-wide scanning to catch leaked credentials.
- **Medium risk – Reviewer/signature settings unknown:** Detailed protection settings are inaccessible (`403` at the protection endpoint), leaving required reviewers, force-push blocks, and signed-commit enforcement unverified. Request an administrator export or screenshot current rules to confirm coverage.
- **Verified – Branch marked protected:** The lightweight branch payload confirms `main` is protected, establishing a baseline guardrail even though enforcement depth remains unclear.
