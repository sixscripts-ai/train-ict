---
description: Pipeline to fetch, parse, and ingest ICT 2022 Mentorship transcripts/notes.
---

# Ingest ICT 2022 Mentorship Transcripts

This workflow automates the collection of educational material for the 2022 Mentorship.

## Steps

1. **Discovery** (Completed):
   - Found high-quality notes at: `https://arjoio.notion.site/ICT-2022-Mentorship-Notes-97a31979307a48f5ab11bc553fb04ffe`
   - Structure includes toggleable sections for Episodes 1-41.

2. **Extraction**:
   - *Action*: Use `browser_subagent` to visit the identified page.
   - *Action*: navigate to each episode's section.
   - *Action*: Copy the text content.

3. **Storage**:
   - *Action*: Save the raw content to `knowledge_base/resources/documents/transcripts/episode_XX.md`.

4. **Processing**:
   - *Action*: Read the saved file.
   - *Action*: Extract key rules, patterns, and definitions.
   - *Action*: specific "Missing Concepts" to `knowledge_base/concepts/`.
   - *Action*: Update `knowledge_base/models/ict_2022_mentorship.md` with nuances found in the transcript.

5. **Verification**:
   - *Action*: User confirms that the extracted data looks correct.
