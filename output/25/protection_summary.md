# Repository Protection Summary

## Branch Protection (main)
- `main` is marked as `protected: true`, confirming that the branch has at least one protection rule applied (source: `gh api repos/tbrandenburg/shai/branches/main`).
- The lightweight protection payload reports `protection.enabled: false` and `required_status_checks.enforcement_level: off`, which means no status checks are enforced through the API response we can access. Full reviewer/force-push/dismissal settings remain unknown because they require elevated permissions.
- Directly querying the detailed branch-protection endpoint fails with `HTTP 403 Resource not accessible by integration`, so we cannot confirm whether required reviewers, signed commits, or other protections are configured. This gap should be validated by a repository administrator.

## Secret Scanning & Security Features
- The repository metadata does not return a `security_and_analysis` block, implying GitHub Advanced Security features such as secret scanning and code scanning are not enabled (or visibility is restricted) for `tbrandenburg/shai`.
- Calling the secret-scanning alerts API (`gh api repos/tbrandenburg/shai/secret-scanning/alerts`) also returns `HTTP 403 Resource not accessible by integration`, so current alert status cannot be observed. An org admin must verify whether secret scanning and push protection are turned on.

## Evidence Commands
```
$ gh api repos/tbrandenburg/shai/branches/main
$ gh api repos/tbrandenburg/shai/branches/main/protection  # → 403
$ gh api repos/tbrandenburg/shai/secret-scanning/alerts?per_page=1  # → 403
```
