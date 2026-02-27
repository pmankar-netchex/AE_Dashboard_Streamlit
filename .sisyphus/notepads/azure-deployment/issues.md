# Issues — azure-deployment

## [2026-02-26] Pre-execution Issues Found (Atlas)

### ISSUE-001: .gitignore ignores .streamlit/config.toml
- **File**: `.gitignore` line 2
- **Problem**: `.streamlit/config.toml` is in `.gitignore`. If not fixed, the Streamlit
  production config won't be committed to git, and CI/CD Docker builds won't have it.
- **Fix**: Task 1 agent must ALSO modify `.gitignore` to remove or negate this line.
  Add `!.streamlit/config.toml` after the existing `.streamlit/config.toml` line,
  OR remove the `.streamlit/config.toml` line entirely from .gitignore.
- **Status**: Must be addressed in Task 1

### ISSUE-002: az bicep CLI may not be installed
- **Problem**: QA scenarios for Task 3 call `az bicep build`. If az CLI or bicep extension
  not installed in the execution environment, this will fail.
- **Fix**: Task 3 agent should check for `az bicep` first; if not available, use alternative
  validation (parse JSON from compile output, or check Bicep syntax manually).
  Evidence should note if az bicep was unavailable.
- **Status**: Known, agents must handle gracefully

### ISSUE-003: Docker daemon may not be running
- **Problem**: Task 5 and F3 require Docker build/run. If Docker is not running, QA fails.
- **Fix**: Agents should check `docker info` first. If Docker unavailable, note in evidence
  and skip container runtime tests (but still verify Dockerfile syntax).
- **Status**: Known, agents must handle gracefully
