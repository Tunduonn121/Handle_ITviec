import json
from services.aliases import is_skill_match, clean_and_normalize
from core.config import ollama_client as client, MODEL_NAME

# =====================================================================
# CON ĐƯỜNG 1: DFS PRUNE XÁC ĐỊNH (skill-set precompute) + TÙY CHỌN LLM
# ĐỊNH TUYẾN NGỮ NGHĨA Ở TẦNG CATEGORY.
#
# - Tầng Category & Subcategory: prune bằng phép GIAO skill-set (KHÔNG gọi LLM)
#   -> chính xác, miễn phí, không hallucinate, không rate limit.
# - (TÙY CHỌN) Nếu use_llm_routing=True: khi 1 Category bị deterministic loại,
#   hỏi LLM xem Category đó có liên quan ngữ nghĩa không (bù từ vựng alias bỏ sót).
#   Chỉ ~1 lời gọi/Category bị-miss -> rất ít, khó đụng rate limit.
# =====================================================================

# Cache cho lớp LLM định tuyến (chỉ dùng khi bật use_llm_routing)
LLM_ROUTING_CACHE = {}

def clear_pruning_cache():
    """Xóa cache khi cây được nạp lại (hot-reload)."""
    global LLM_ROUTING_CACHE
    LLM_ROUTING_CACHE = {}
    print("🧹 [CACHE] Đã xóa LLM_ROUTING_CACHE do cây được nạp lại.")


def _gap_hits_skillset(gap_dict, node_skills):
    """XÁC ĐỊNH: gap có giao với skill-set (đã precompute & chuẩn hóa) của nhánh không."""
    for gap_skill in gap_dict.keys():
        g = clean_and_normalize(gap_skill)
        for ns in node_skills:
            if is_skill_match(g, ns):
                return True
    return False


def _llm_category_relevant(category_name, gap_skills):
    """TÙY CHỌN: hỏi LLM xem Category có liên quan ngữ nghĩa tới gap không (1 lời gọi, có cache)."""
    cache_key = category_name.lower().strip()
    if cache_key in LLM_ROUTING_CACHE:
        return LLM_ROUTING_CACHE[cache_key]

    skills_str = ", ".join(gap_skills)
    prompt = (
        f'Danh mục khóa học: "{category_name}".\n'
        f'Người dùng đang thiếu các kỹ năng: {skills_str}.\n'
        f'Danh mục này có khả năng chứa khóa học dạy MỘT TRONG các kỹ năng đó không? '
        f'Chỉ trả lời một từ: YES hoặc NO.'
    )
    try:
        response = client.chat(
            model=MODEL_NAME, messages=[{'role': 'user', 'content': prompt}],
            stream=False, options={'temperature': 0.0}
        )
        import re
        answer = response['message']['content'].strip().upper()
        result = bool(re.search(r'\bYES\b', answer))
        LLM_ROUTING_CACHE[cache_key] = result
        return result
    except Exception as e:
        print(f"   ⚠️ [FAIL-OPEN] LLM định tuyến lỗi ở '{category_name}': {e} -> coi là RELEVANT.")
        return True  # KHÔNG cache lỗi


def dfs_tree_search(course_tree, gap_dict, use_llm_routing=False):
    """
    Duyệt cây (DFS theo Category -> Subcategory), prune bằng skill-set xác định.
    Trả về danh sách khóa học ứng viên (course_info dict) cho bước ranking.
    """
    candidate_courses = []
    gap_skills = list(gap_dict.keys())

    for cat, cat_node in course_tree.items():
        det_hit = _gap_hits_skillset(gap_dict, cat_node["_skills"])

        if det_hit:
            # Category liên quan (xác định) -> prune CHẶT ở tầng Subcategory (2 tầng)
            for sub_node in cat_node["_subs"].values():
                if _gap_hits_skillset(gap_dict, sub_node["_skills"]):
                    candidate_courses.extend(sub_node["_courses"])

        elif use_llm_routing and _llm_category_relevant(cat, gap_skills):
            # Deterministic MISS nhưng LLM bảo có liên quan ngữ nghĩa
            # -> gom CẢ Category (1 tầng) để không bỏ sót khớp ngữ nghĩa.
            # (Ranker sẽ lọc tinh lại bằng is_skill_match sau.)
            print(f"   🧭 [LLM-ROUTE] Category '{cat}' được giữ nhờ định tuyến ngữ nghĩa.")
            for sub_node in cat_node["_subs"].values():
                candidate_courses.extend(sub_node["_courses"])

    return candidate_courses


if __name__ == "__main__":
    # ===== TEST LOGIC PRUNE BẰNG CÂY GIẢ (không cần DB/LLM) =====
    fake_tree = {
        "DevOps": {
            "_skills": {"docker", "kubernetes", "ci/cd"},
            "_subs": {
                "Containers": {"_skills": {"docker", "kubernetes"},
                               "_courses": [{"course_id": "C1", "title": "Docker 101", "level": 1, "target_skills": ["Docker"]}]},
                "Pipelines": {"_skills": {"ci/cd"},
                              "_courses": [{"course_id": "C2", "title": "CI/CD", "level": 2, "target_skills": ["CI/CD"]}]},
            },
        },
        "Frontend": {
            "_skills": {"reactjs", "javascript"},
            "_subs": {
                "React": {"_skills": {"reactjs"},
                          "_courses": [{"course_id": "C3", "title": "React", "level": 2, "target_skills": ["ReactJS"]}]},
            },
        },
    }
    gap = {"docker": [1, 2]}
    res = dfs_tree_search(fake_tree, gap, use_llm_routing=False)
    print("Gap = Docker. Khóa ứng viên (chỉ nên có C1 từ sub 'Containers'):")
    for c in res:
        print(f"  {c['course_id']} - {c['title']}")
    assert {c["course_id"] for c in res} == {"C1"}, "SAI: prune không đúng!"
    print("✅ Prune xác định đúng: chỉ lấy sub 'Containers', bỏ 'Pipelines' và cả 'Frontend'.")