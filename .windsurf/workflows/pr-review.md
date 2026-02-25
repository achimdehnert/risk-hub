---
description: Review and address PR comments using GitHub MCP
---

# PR Review Workflow

## Steps

1. List open PRs:

```
mcp7_list_pull_requests owner=achimdehnert repo=risk-hub state=open
```

2. Get PR details and files changed:

```
mcp7_get_pull_request owner=achimdehnert repo=risk-hub pull_number=<N>
mcp7_get_pull_request_files owner=achimdehnert repo=risk-hub pull_number=<N>
```

3. Review comments:

```
mcp7_get_pull_request_comments owner=achimdehnert repo=risk-hub pull_number=<N>
```

4. Address each comment by making code changes

5. Push fixes and respond to comments
