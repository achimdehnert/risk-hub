---
description: Create new ADR with automatic scope detection and proper structure
---

Inputs: Title (short), context description.

1. Determine next ADR number:
   // turbo
   ls docs/adr/ADR-0*.md | sort -t- -k2 -n | tail -1
   Extract the highest number and increment by 1.

2. Generate filename: `ADR-{NNN}-{title-kebab-case}.md`

3. Create the ADR file with this template:

   ```markdown
   # ADR-{NNN}: {Title}

   | Metadata | Value |
   |----------|-------|
   | **Status** | Proposed |
   | **Date** | {today YYYY-MM-DD} |
   | **Author** | Achim Dehnert |
   | **Reviewers** | — |
   | **Supersedes** | — |
   | **Related** | {detect related ADRs from context} |

   ---

   ## 1. Context
   {User-provided context description}

   ## 2. Decision
   {To be filled}

   ## 3. Implementation
   {To be filled}

   ## 4. Consequences
   ### 4.1 Positive
   ### 4.2 Negative
   ### 4.3 Mitigation

   ## 5. Changelog
   | Date | Author | Change |
   |------|--------|--------|
   | {today} | Achim Dehnert | Initial draft |
   ```

4. Open the created file for editing.

5. Print: "Created ADR-{NNN} at docs/adr/{filename}"
