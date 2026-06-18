import json
import re
from typing import Dict, List, Tuple
from services.aliases import GLOBAL_ALIAS_MAP, clean_and_normalize

def _safe_token_match(a: str, b: str) -> bool:
    """Khớp an toàn: bằng nhau, hoặc a là 1 token/cụm độc lập trong b (không cắt giữa từ)."""
    a, b = a.strip().lower(), b.strip().lower()
    if a == b:
        return True
    # word-boundary tự chế, an toàn cho c#, c++, .net
    pat = r'(?<![a-z0-9])' + re.escape(a) + r'(?![a-z0-9])'
    return re.search(pat, b) is not None

# =====================================================================
# KHỐI 1: BỘ TỪ ĐIỂN ĐỒNG NGHĨA (ALIAS RESOLVER)
# Mục đích: Tìm tất cả các "anh em họ hàng" của một kỹ năng. 
# Ví dụ: Nhập vào "React", hàm sẽ trả về ["React", "ReactJS", "React.js"]
# =====================================================================
def get_skill_aliases(skill: str) -> List[str]:
    skill_clean = skill.strip().lower()
    # Tìm tất cả các từ khóa gốc trỏ về cùng một giá trị đích
    target_val = GLOBAL_ALIAS_MAP.get(skill_clean, skill_clean)
    aliases = [k for k, v in GLOBAL_ALIAS_MAP.items() if v == target_val]
    if target_val not in aliases:
        aliases.append(target_val)
    return aliases

# =====================================================================
# KHỐI 2: HÀM TÌM KIẾM KỸ NĂNG TRONG CV (SKILL MATCHER)
# Mục đích: Quét xem ứng viên có sở hữu kỹ năng đang xét (hoặc các từ 
# đồng nghĩa của nó) hay không, và trả về Level cao nhất mà ứng viên đạt được.
# =====================================================================
def find_matching_skill(skill_to_find: str, available_skills: Dict) -> Tuple:
    skill_to_find = skill_to_find.strip()
    
    def get_level(value):
        if isinstance(value, dict): return value.get("level", 0)
        return value

    # Gộp từ khóa gốc và các từ đồng nghĩa vào một mảng để tìm kiếm
    search_terms = [skill_to_find.lower()] + [a.lower() for a in get_skill_aliases(skill_to_find)]
    best_match_name = None
    best_match_level = 0

    # Quét toàn bộ kho kỹ năng của ứng viên
    for available_skill, info in available_skills.items():
        available_skill_lower = available_skill.lower()
        cv_lvl = get_level(info)
        
        # Nếu trúng từ khóa và level cao hơn mức đang lưu thì cập nhật
        for term in search_terms:
            if _safe_token_match(term, available_skill_lower):
                if cv_lvl > best_match_level:
                    best_match_level = cv_lvl
                    best_match_name = available_skill

    if best_match_name:
        return best_match_name, best_match_level
    return None, 0

# =====================================================================
# KHỐI 3: HÀM TÁCH MỆNH ĐỀ PHỨC TẠP (COMPLEX CLAUSE PARSER)
# Mục đích: Bóc tách các cụm kỹ năng lồng nhau. 
# VD: "Java (Spring Boot, Hibernate)" -> ["Java", "Spring Boot", "Hibernate"]
# =====================================================================
def parse_complex_candidate(candidate_str: str) -> List[str]:
    match = re.match(r'([^\(]+)(?:\((.*)\))?', candidate_str)
    if not match: 
        return [candidate_str.strip()]
    
    skills = [match.group(1).strip()]
    if match.group(2):
        sub_skills = [s.strip() for s in match.group(2).split(',')]
        skills.extend(sub_skills)
    return skills

# =====================================================================
# KHỐI 4: TRÁI TIM CỦA THUẬT TOÁN - TÍNH TOÁN SKILL GAP
# Mục đích: So khớp JD (yêu cầu) và CV (năng lực), tính toán khoảng cách 
# và đề xuất lộ trình. Xử lý cực kỳ chặt chẽ logic EXACT (Bắt buộc) 
# và ANY (Tự chọn 1 trong các nhánh).
# =====================================================================
def compute_skill_gap(cv_skills_assessed: Dict, jd_skills: Dict) -> Tuple[Dict, Dict]:
    matched = {} # Chứa các kỹ năng đã thỏa mãn
    gap = {}     # Chứa các kỹ năng bị hổng
    
    for skill_key, jd_info in jd_skills.items():
        level_required = jd_info.get("level", 1) if isinstance(jd_info, dict) else jd_info
        match_mode = jd_info.get("match_mode", "EXACT") if isinstance(jd_info, dict) else "EXACT"
        
        # ---------------------------------------------------------
        # CHẾ ĐỘ 'ANY' - XỬ LÝ MỆNH ĐỀ HOẶC (VD: C# | Java | Python)
        # ---------------------------------------------------------
        if match_mode == "ANY":
            candidates = [s.strip() for s in skill_key.split("|")]
            
            best_branch = None
            best_branch_score = -1
            best_branch_missing = []
            is_complex = False
            
            # Quét từng nhánh (VD: quét nhánh C#, sau đó quét nhánh Java)
            for candidate in candidates:
                req_skills = parse_complex_candidate(candidate)
                if len(req_skills) > 1:
                    is_complex = True
                    
                branch_score = 0
                branch_missing = []
                
                # Tính điểm cho nhánh hiện tại dựa trên năng lực CV
                for rs in req_skills:
                    found_skill, found_level = find_matching_skill(rs, cv_skills_assessed)
                    if found_level >= level_required:
                        branch_score += 1
                    else:
                        if found_level > 0:
                            branch_score += 0.5 # Cho điểm khuyến khích nếu có biết chút ít
                        branch_missing.append((rs, found_level, found_skill))
                        
                # Cập nhật nhánh TỐT NHẤT (ít phải học lại nhất) cho người dùng
                if branch_score > best_branch_score:
                    best_branch_score = branch_score
                    best_branch = candidate
                    best_branch_missing = branch_missing
                elif branch_score == best_branch_score:
                    if len(branch_missing) < len(best_branch_missing):
                        best_branch = candidate
                        best_branch_missing = branch_missing
            
            final_match_mode = "ANY_COMPLEX" if is_complex else "ANY"

            # Nếu nhánh tốt nhất không thiếu gì -> Đạt yêu cầu
            if len(best_branch_missing) == 0:
                matched[skill_key] = {
                    "level_required": level_required,
                    "user_best_match": best_branch,
                    "user_level": level_required,
                    "match_mode": final_match_mode,
                    "status": f"✅ ĐẠT YÊU CẦU (Theo nhánh: {best_branch})" if is_complex else f"✅ ĐẠT YÊU CẦU"
                }
            # Nếu nhánh tốt nhất vẫn thiếu -> Đưa vào danh sách Lỗ hổng (Gap)
            else:
                total_missing_levels = []
                missing_names = []
                
                for ms, curlvl, fname in best_branch_missing:
                    # Tính toán chênh lệch Level (VD: Từ Lvl 1 lên Lvl 3)
                    missing_levels = list(range(curlvl + 1 if curlvl > 0 else 1, level_required + 1))
                    total_missing_levels.extend(missing_levels)
                    display_name = fname if fname else ms
                    missing_names.append(f"{display_name} (Lvl {curlvl}->{level_required})" if curlvl>0 else f"{display_name} (Lvl 1->{level_required})")
                
                # Gợi ý text cho Frontend hiển thị
                if best_branch_score == 0:
                    rec_text = f"Học 1 trong [{', '.join(candidates)}] từ đầu." if not is_complex else f"Chưa biết gì. Gợi ý chọn nhánh '{best_branch}' và học từ đầu: " + ", ".join(missing_names)
                else:
                    rec_text = f"Đang theo '{best_branch}'. Cần học thêm: " + ", ".join(missing_names) if is_complex else f"Nâng {best_branch} lên Level {level_required} hoặc đổi qua: {', '.join(candidates)}"
                
                gap[skill_key] = {
                    "level_required": level_required,
                    "candidates": candidates,
                    "user_best_match": best_branch,
                    "user_level": best_branch_score,
                    "missing_levels": total_missing_levels,
                    "match_mode": final_match_mode,
                    "recommendation": rec_text
                }
                
        # ---------------------------------------------------------
        # CHẾ ĐỘ 'EXACT' - BẮT BUỘC PHẢI CÓ (VD: Git, Docker)
        # ---------------------------------------------------------
        else:
            found_skill, user_level = find_matching_skill(skill_key, cv_skills_assessed)
            
            # Nếu CV chưa đạt Level yêu cầu
            if user_level < level_required:
                missing_levels = list(range(user_level + 1 if user_level > 0 else 1, level_required + 1))
                #lấy tên hiển thị của CV nếu có, nếu không thì lấy tên kỹ năng gốc từ JD
                display_name = found_skill if found_skill else skill_key
                rec_text = f"Nâng {display_name} từ Level {user_level} lên {level_required}" if user_level > 0 else f"Học {display_name} từ Level 1 đến {level_required}"
                
                gap[skill_key] = {
                    "level_required": level_required,
                    "user_level": user_level,
                    "user_skill_name": found_skill if user_level > 0 else None,
                    "missing_levels": missing_levels,
                    "match_mode": "EXACT",
                    "recommendation": rec_text
                }
            # Nếu CV thỏa mãn Level
            else:
                matched[skill_key] = {
                    "level_required": level_required,
                    "user_skill_name": found_skill,
                    "user_level": user_level,
                    "match_mode": "EXACT",
                    "status": "✅ ĐẠT YÊU CẦU"
                }
                
    return gap, matched

# =====================================================================
# KHỐI 5: PHÂN LOẠI MỨC ĐỘ ƯU TIÊN VÀ ƯỚC TÍNH THỜI GIAN
# Mục đích: Chia lỗ hổng ra làm 3 loại (Critical, Important, Nice To Have) 
# để lên lộ trình học bài bản. Mặc định 1 Level hổng = 20h học.
# =====================================================================
def get_gap_summary(gap: Dict) -> Dict:
    critical, important, nice_to_have = [], [], []
    total_hours = 0
    
    for skill_key, gap_info in gap.items():
        level_required = gap_info["level_required"]
        missing_count = len(gap_info["missing_levels"])
        hours_estimate = missing_count * 20  
        
        gap_item = {
            "skill": skill_key,
            "level_required": level_required,
            "user_level": gap_info["user_level"],
            "match_mode": gap_info["match_mode"],
            "recommendation": gap_info["recommendation"],
            "hours_estimate": hours_estimate
        }
        
        if level_required == 3: critical.append(gap_item)
        elif level_required == 2: important.append(gap_item)
        else: nice_to_have.append(gap_item)
        
        total_hours += hours_estimate
    
    return {
        "total_gap_count": len(gap),
        "critical": critical,
        "important": important,
        "nice_to_have": nice_to_have,
        "total_hours_estimate": total_hours
    }

# ===== TEST TRẢI NGHIỆM ĐỈNH CAO =====
if __name__ == "__main__":
    cv_skills_assessed = {
        "C#": 3,
        "Python": 2,
        "Java": 3,
        "Spring Boot": 3,
        "SQL Server": 3,
        "MySQL": 2,
        "PostgreSQL": 2,
        "Docker": 2,
        "REST API": 2, 
        "Entity Framework": 2,
        "LINQ to SQL": 1,
        "Flutter": 1,
        "NodeJS": 1,
        "Gitlab CI/CD": 3 # Đã thêm vào để test tính năng X-Quang
    }
    
    jd_skills = {
        ".NET Core": {"level": 3, "match_mode": "EXACT"},
        "SQL Server": {"level": 3, "match_mode": "EXACT"},
        "Java (Spring Boot, Hibernate, Microservices)|Node.js (ExpressJS, NestJS)|Python (Django, FastAPI)": {"level": 3, "match_mode": "ANY"},
        "MySQL|PostgreSQL|Oracle|MongoDB|Redis": {"level": 2, "match_mode": "ANY"},
        "RESTful API|gRPC|GraphQL": {"level": 2, "match_mode": "ANY"}, 
        "AWS|Azure|GCP": {"level": 1, "match_mode": "ANY"},
        "Kubernetes": {"level": 1, "match_mode": "EXACT"},
        "Docker": {"level": 1, "match_mode": "EXACT"},
        "CI/CD": {"level": 1, "match_mode": "EXACT"}, 
        "GitHub|GitLab": {"level": 2, "match_mode": "ANY"}
    }
    
    print("=" * 80)
    gap, matched = compute_skill_gap(cv_skills_assessed, jd_skills)

    print("\n🟢 SKILLS ĐÃ ĐÁP ỨNG XUẤT SẮC (MATCHED):")
    for skill, info in matched.items():
        if info['match_mode'] == 'ANY_COMPLEX':
            print(f"  ✅ Nhóm: {skill[:30]}... -> {info['status']}")
        elif info['match_mode'] == 'ANY':
            print(f"  ✅ {skill} (Yêu cầu Lvl {info['level_required']}) -> Có '{info['user_best_match']}' đạt Lvl {info['user_level']}")
        else:
            print(f"  ✅ {skill} (Yêu cầu Lvl {info['level_required']}) -> Đạt Lvl {info['user_level']}")

    summary = get_gap_summary(gap)
    
    print("\n" + "=" * 80)
    print("🚨 NHỮNG KỸ NĂNG CẦN HỌC ĐỂ LẤY JOB NÀY:")
    
    if summary["critical"]:
        print("\n🔴 CRITICAL (Bắt buộc Level 3):")
        for item in summary["critical"]:
            print(f"  - {item['recommendation']} ⏱️ ({item['hours_estimate']}h)")
            
    if summary["important"]:
        print("\n🟡 IMPORTANT (Level 2):")
        for item in summary["important"]:
            print(f"  - {item['recommendation']} ⏱️ ({item['hours_estimate']}h)")
            
    if summary["nice_to_have"]:
        print("\n🔵 NICE TO HAVE (Level 1):")
        for item in summary["nice_to_have"]:
            print(f"  - {item['recommendation']} ⏱️ ({item['hours_estimate']}h)")
            
    print(f"\n⏱️ TỔNG THỜI GIAN DỰ KIẾN: {summary['total_hours_estimate']} giờ học")
    print("=" * 80)# ===== BÀN TEST DÀNH RIÊNG CHO LỜI KHUYÊN (rec_text) =====
if __name__ == "__main__":
    # Đóng giả một ứng viên có kỹ năng dở dang
    cv_test = {
        "Python": 1,          # Biết sơ sơ Python
        "Java": 2,            # Đang theo hệ Java khá vững
        "Spring Boot": 2      # Biết dùng Spring Boot
        # Hoàn toàn mù tịt Ruby, PHP, NodeJS, C#
    }
    
    # 4 Kịch bản JD đánh đúng vào 4 dòng if/else của Sếp
    jd_test = {
        # KỊCH BẢN 1: Chưa biết môn nào trong list, và list này KHÔNG lồng ghép
        "Ruby|Go|Rust": {"level": 2, "match_mode": "ANY"},
        
        # KỊCH BẢN 2: Chưa biết môn nào, và list này CÓ lồng ghép phức tạp
        "PHP (Laravel, MySQL)|NodeJS (Express, MongoDB)": {"level": 2, "match_mode": "ANY"},
        
        # KỊCH BẢN 3: Đã biết 1 môn trong list (Python Lvl 1), list KHÔNG lồng ghép
        "Python|C#|C++": {"level": 3, "match_mode": "ANY"},
        
        # KỊCH BẢN 4: Đã biết 1 nhánh (Java), list CÓ lồng ghép phức tạp
        "Java (Spring Boot, Hibernate)|C# (.NET Core, SQL Server)": {"level": 3, "match_mode": "ANY"}
    }
    
    gap, matched = compute_skill_gap(cv_test, jd_test)
    summary = get_gap_summary(gap)
    
    print("=" * 80)
    print("🎯 DEMO 4 KỊCH BẢN LỜI KHUYÊN (rec_text) ĐỂ BẮT FRONTEND HIỂN THỊ:")
    print("=" * 80)
    
    # Gộp tất cả các rổ hổng lại để in ra cho dễ nhìn
    all_gaps = summary["critical"] + summary["important"] + summary["nice_to_have"]
    
    for i, item in enumerate(all_gaps, 1):
        print(f"\n[KỊCH BẢN {i}] Yêu cầu JD: {item['skill']}")
        print(f"👉 Dòng rec_text sinh ra: \033[92m{item['recommendation']}\033[0m")