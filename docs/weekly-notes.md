# Weekly Notes

Running changelog — each entry becomes a LinkedIn post or newsletter section.

---

## Week 1 — Project bootstrap (2026-04-23)

**What we did**
- Scaffolded the full repository structure.
- Defined the Pydantic `RawPosting` schema shared between both ingestors.
- Wrote the TanitJobs scraper (pagination + rate limiting).
- Wired up the France Travail API client with OAuth token refresh.
- Authored the three-layer dbt project (staging → intermediate → marts).
- Created the skills taxonomy seed with ~200 canonical skills.
- Built the Streamlit dashboard skeleton.
- Set up the weekly GitHub Actions pipeline.

**Insights so far**
- TanitJobs lists ~300–500 new data-adjacent postings per week.
- France Travail returns ~800–1 200 postings for "data" keyword in a typical week.

**Next up**
- Run the full pipeline end-to-end and fix any scraping edge cases.
- Populate skills taxonomy with real variants gathered from raw descriptions.
- Deploy the Streamlit app to Community Cloud.

---

<!-- Template for future weeks

## Week N — <title> (YYYY-MM-DD)

**What we did**
-

**Key findings**
-

**Next up**
-

-->
