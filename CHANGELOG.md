# Changelog / Pre-Handover Verification Checklist

Confirmed via live test run during development (safe to trust):

- [x] Removed disjunctive (ANY) skill matching from `compute_skill_gap()` —
      now EXACT-only. Extraction prompt updated to cap "choose-one" group
      levels at 2, with a "Nice to have" exception forcing level 1. Verified
      by re-running `skill_extractor.py` against the sample JD twice; output
      matched expected levels both times.
- [x] Confirmed via direct SQL query: `Course_Skills` has no `Level` column;
      course proficiency is course-level, not skill-level. Documented in
      README Known Limitations and IEEE paper.

Recommended earlier in development — VERIFY these are actually applied in
the final code before shipping (not confirmed via a final test run):

- [ ] `course_ranker.py` performance fix: memoized skill normalization
      (`_NORM_CACHE`, `lru_cache` on `clean_and_normalize`) to fix an O(n²)
      bottleneck that caused ranking to take ~163s on a large candidate
      pool. If not applied, profile `rank_courses_with_llm()` before
      shipping — do not assume it is fast.
- [ ] Misleading print/comment in `background_tasks.py`
      ("🏆 Đang gọi Qwen xếp hạng...") — should read "(deterministic, no
      LLM)" since ranking makes no model call. Cosmetic but important for
      anyone reading logs and assuming LLM involvement.
- [ ] `extract_skills_from_cv()` prompt — verify it is NOT accidentally
      reusing the JD prompt text / `jd_text_safe` variable. This bug was
      identified once during development; confirm the fix is in place by
      running `extract_skills_from_cv()` standalone and checking it doesn't
      crash with a `NameError`.
- [ ] Course tree structure: confirm "Front-End" is a top-level domain
      sibling to "Back-End" and "DevOps & Cloud", not nested under DevOps.
      (This was a diagramming error, not necessarily a data error — verify
      against `tree_builder.py` / `auto_categorize_db.py` output directly.)