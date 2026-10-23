# ITviec_Mini — Progressive Skill-Gap Analysis & Course Recommendation

Graduation project by Nguyễn Tùng Dương (2280600389, 22DTHQA1, HUTECH International
Standard Program), supervised by Dr. Lê Thị Ngọc Thơ. An academic paper based on
this work was submitted to [IEEE conference name/TBD].

## 1. Overview

This system reads a candidate's CV and a job description (JD), computes a
**level-aware skill gap**, and recommends a Top-K course learning path to close
that gap. The architecture is **deterministic-first**: a Large Language Model
(Qwen3-Coder-480B, via Ollama cloud) is used *only* to extract skills and
proficiency levels from unstructured text. Every subsequent stage — gap
computation, course retrieval, and ranking — is deterministic Python with no
model calls, which makes the system fast, cheap, and fully reproducible.

The method is positioned as a deterministic variant of LLMTreeRec (COLING 2025):
it keeps the idea of a hierarchical item tree, but replaces LLM-routed branch
decisions with a plain skill-set intersection test.

## 2. System Requirements

- Python 3.10+
- SQL Server (developed against a named instance, e.g. `HOST\INSTANCE`)
- Node.js 18+ and npm (for the React frontend)
- An Ollama cloud account / API key for `qwen3-coder:480b` (or equivalent
  access to the configured `MODEL_NAME` in `core/config.py`)

## 3. Installation

```bash
# Backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

Copy `.env.example` to `.env` and fill in real values:
```bash
cp .env.example .env
```
Required variables (see `core/config.py` for the authoritative list):
- `OLLAMA_API_KEY`
- `MODEL_NAME` (currently `qwen3-coder:480b`)
- SQL Server connection string / credentials

**Never commit `.env` with real credentials.**

## 4. Database Setup

Schema (confirmed via `INFORMATION_SCHEMA.COLUMNS`):

| Table | Key columns |
|---|---|
| `Courses` | `CourseID`, `Title`, `Description`, `URL`, `CourseLevel`, `level`, `CategoryID`, `SubcategoryID` |
| `Course_Skills` | `CourseID`, `SkillID` (junction table — **no level column**, see Known Limitations) |
| `Skills` | `SkillID`, `SkillName` |
| `Job_Skills` | `JobID`, `SkillID`, `RequiredLevel` |
| `User_Skills` | `UserID`, `SkillID`, `CurrentLevel` |

```bash
# Run in order:
sqlcmd -S <server> -i database/schema.sql
sqlcmd -S <server> -i database/seed_sample.sql   # ~50-100 sample rows for testing
```

The full 5,856-course catalogue is **not** included in this handover (size +
possible ToS concerns re: redistributing scraped Coursera data). To
regenerate it, run the crawl pipeline — see Section 6, steps 1–2.

## 5. Running the System

```bash
uvicorn main:app --reload
```
On successful start, you should see:
⏳ Đang nạp Database và xây dựng Cây Khóa Học lên RAM...
✅ KHỞI ĐỘNG THÀNH CÔNG: Cây Khóa Học đã sẵn sàng trên RAM!

Then start the frontend:
```bash
cd frontend && npm run dev
```

**Before any live demo:** the extraction LLM call can be slow on a cold
connection. Run 1–2 warm-up requests a few minutes before demoing.

## 6. Code Structure — Read in This Order

The pipeline has an offline phase (run once, builds the course tree) and an
online phase (runs per request). Read the files in this order to understand
the system:

**Offline (catalogue preparation):**
1. `services/coursera_crawler.py` — scrapes course listings from Coursera
2. `services/cleansing_batch.py` — normalizes skill names, removes noise
3. `services/auto_categorize_db.py` — LLM classifies each course into the
   fixed 11-category / subcategory schema
4. `services/import_courses_to_sql.py` — writes cleaned courses to SQL Server
5. `services/tree_builder.py` — loads the catalogue into an in-memory tree at
   start-up; annotates every node with its aggregate skill set

**Online (per-request pipeline):**
6. `services/aliases.py` — `clean_and_normalize()`, `is_skill_match()`,
   `GLOBAL_ALIAS_MAP` — canonicalizes skill name variants
7. `services/skill_extractor.py` — `extract_skills_from_jd()`,
   `extract_skills_from_cv()` — the only module calling the LLM; includes the
   extraction prompt, `validate_extraction()` output validation
8. `services/skill_gap_calculator.py` — `compute_skill_gap()` — the
   progressive gap algorithm (EXACT-only; see Known Limitations)
9. `services/tree_searcher.py` — `dfs_tree_search()` — deterministic
   skill-set-pruned DFS retrieval
10. `services/course_ranker.py` — `rank_courses_with_llm()` (name is
    historical — **this function is fully deterministic**, no LLM call for
    course selection), `find_combo_courses()`, `group_courses_by_gap()`,
    `_relevance_score()`
11. `services/evaluator.py` — `E(c)` guardrail scoring,
    `log_live_evaluation_metrics()`
12. `services/background_tasks.py` — `process_llm_logic()` — orchestrates
    the full pipeline per request; entry point to trace if debugging
    end-to-end behavior

Supporting:
- `services/check_missed_skills.py` — audits which raw keywords get filtered
  by the blacklist, to help refine it over time
- `services/test_pipeline.py` — standalone smoke test

## 7. Data

| File | Contents |
|---|---|
| `data/gold_skills_131.csv` | 131 gold-standard skills for 36 JDs (P1 ground truth) |
| `data/labeled_pairs_36.csv` | 595 course-relevance labels across 36 CV–JD pairs (P3–P5 ground truth) |
| `data/synthetic_100_pairs/` | 100 synthetic CV–JD pairs, 15 professional domains (e.g. Backend Java, Frontend React, DevOps, Data/AI, Security), 3 gap types |

**Labeling protocol** (see `docs/labeling_protocol.md` for full detail): the
course title or the JD's explicit wording was the primary evidence for every
relevance decision; an AI tool assisted analysis but a human made the final
call on every label. A second independent annotator and inter-rater agreement
(e.g. Cohen's κ) were not performed — flagged as future work.

**Note:** the 15 professional domains (used to construct CV–JD test data) and
the 11 course-catalogue categories (used to organize the course tree) are
*two separate taxonomies* for two different purposes — do not conflate them.

## 8. Key Results (see thesis / IEEE paper for full detail)

| Experiment | Compares | Key result |
|---|---|---|
| P1 — Extraction | LLM vs. keyword baseline | F1 96.7% vs. 84.4% |
| P2 — Tokens | Filter vs. tree | −99.8% from filter; tree contributes +0.0% further |
| P3 — End-to-end + guardrail | With/without E(c) | 74.8% precision; E(c) ablation: 0.0 pp change |
| P4 — Retrieval | Deterministic vs. LLM-routed pruning | 99.2% vs. 63.3% recall, ~25× faster, 0 LLM calls |
| P5 — Ranking | Deterministic vs. LLM ranking | 75.4% vs. 73.8% precision, Jaccard 1.000 vs. 0.938 |

## 9. Known Limitations (confirmed, read before extending the system)

1. **Disjunctive ("A or B") requirements are not fully modeled.** The gap
   computation only handles mandatory (EXACT) requirements. A JD requiring
   "proficient in one of Java, Node.js, or Python" is extracted with every
   listed technology capped at level 2 to avoid overstating the requirement
   — this is a heuristic approximation, not a true "choose-one" mechanism.
   See `skill_extractor.py` prompt rules and IEEE paper Threats to Validity.

2. **Course proficiency is per-course, not per-skill.** `Course_Skills` has
   no `Level` column — `Courses.level` is one value applied uniformly to
   every skill that course teaches. Confirmed by direct query: a single
   course teaching 8 distinct skills carries one identical level across all
   8. Contrast with `Job_Skills.RequiredLevel` / `User_Skills.CurrentLevel`,
   which *are* per-skill.

3. **Skill tagging on courses can be coarse.** Multi-part or multi-language
   variants of the same course series sometimes receive a near-identical,
   broad skill set rather than skills specific to each part's actual
   content (observed directly in `Course_Skills` data for Kubernetes/GKE
   course series).

4. **Evaluation is on a synthetic test set with single-annotator labeling.**
   Real-world CVs/JDs have messier formatting; results may not fully
   transfer. See IEEE paper Section 4 (Threats to Validity) for complete
   discussion.

## 10. Suggested Next Steps (Future Work)

1. Reintroduce a lightweight disjunctive (`ANY`) mechanism for "choose-one"
   requirements without the full branch-scoring complexity that was removed.
2. Move from the fixed-schema tree to a knowledge graph (e.g. Neo4j) so one
   course can connect to multiple domains.
3. Add per-skill course-level annotation (requires schema change:
   `Course_Skills` needs a `Level` column, likely LLM-inferred per
   skill-course pair rather than inherited from `Courses.level`).
4. Automated catalogue maintenance (scheduled re-crawl + re-classification).
5. Local LLM deployment to remove the cloud dependency at extraction.
6. A second independent annotator + Cohen's κ for the ground truth.

## 11. Contact

Nguyễn Tùng Dương — [email] — GitHub: [link]
Supervisor: Dr. Lê Thị Ngọc Thơ