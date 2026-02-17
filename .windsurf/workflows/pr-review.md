---
description: Review and address PR comments using GitHub MCP
---

Inputs: PR number.

1. Fetch PR details using GitHub MCP:
   Use mcp7_get_pull_request to get PR title, body, base/head branches.
   Print summary of the PR.

2. Fetch changed files:
   Use mcp7_get_pull_request_files to list all changed files.
   Print file list with additions/deletions count.

3. Fetch review comments:
   Use mcp7_get_pull_request_comments to get all review comments.
   If no comments, report "No review comments found" and STOP.

4. For each review comment:
   a. Read the referenced file at the commented line.
   b. Understand the reviewer's request.
   c. Implement the requested change using the edit tool.
   d. After fixing, print: "Fixed: <file>:<line> — <summary>"

5. After all comments addressed:
   // turbo
   cd src && python -m pytest --tb=short -q
   If tests fail, report which tests broke and suggest fixes.

6. Stage and summarize all changes:
   // turbo
   git diff --stat
   Print a commit message suggestion following: `fix: address PR #<number> review comments`
