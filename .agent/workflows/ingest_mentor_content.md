---
description: Ingest any ICT content (text/url), extract rules, and check code coverage
---

1. [INPUT REQUIRED] - The user provides a URL or Raw Text of the content.
   - *Prompt*: "What is the content source? (Paste URL or Text)"

2. Extract Intelligence
   - If URL: Use `browser_subagent` or `read_url_content` to fetch text.
   - If Text: Proceed directly.
   - *Goal*: Identify specific **Trading Rules** (If X then Y) and **Definitions**.

3. Check Code Coverage
   - *Action*: Search the `src/ict_agent` directory for keywords found in the content.
   - *Action*: Compare the *extracted rules* vs the *implemented logic* in Python files.
   - *Example*: "Content says FVG needs 3 candles. Code says `min_gap_candles=1`. DISCREPANCY DETECTED."

4. Generate Implementation Plan
   - Create a file `implementation_plan_YYYYMMDD.md`.
   - List **New Concepts** (not in code).
   - List **Refinements** (logic changes needed).

5. Update Knowledge Base
   - Summarize the content into `knowledge_base/resources/learning_journal.md`.
