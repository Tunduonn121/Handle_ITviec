import re
# Gọi két sắt để lấy dữ liệu chung (Đã gộp import chuẩn Clean Architecture)
import core.state as state

# Import các công nhân chuyên trách (AI, Toán học, Duyệt cây)
from services.skill_extractor import extract_skills_from_jd, extract_skills_from_cv
from services.skill_gap_calculator import compute_skill_gap
from services.tree_searcher import dfs_tree_search
from services.course_ranker import rank_courses_with_llm
from services.aliases import clean_and_normalize

def process_llm_logic(task_id: str, cv_text: str, jd_text: str, verified_skills: dict = None, pre_extracted_jd: dict = None):
    """
    Trái tim của hệ thống: Dây chuyền sản xuất tự động (End-to-End Pipeline).
    Chạy ngầm ở background để không làm treo giao diện của người dùng.
    """
    try:
        print(f"\n🚀 [TASK {task_id}] BẮT ĐẦU LUỒNG PHÂN TÍCH TOÀN TRÌNH")
        
        # =====================================================================
        # BƯỚC 1: TRÍCH XUẤT KỸ NĂNG (SKILL EXTRACTION)
        # Mục đích: Biến văn bản thô (Text) thành Dữ liệu có cấu trúc (JSON).
        # Tối ưu: Nếu Frontend đã truyền sẵn JSON (pre_extracted) thì bỏ qua bước gọi LLM để tiết kiệm tiền/thời gian.
        # =====================================================================
        if pre_extracted_jd:
            jd_skills = pre_extracted_jd
        else:
            jd_skills = extract_skills_from_jd(jd_text)

        if verified_skills:
            cv_skills = verified_skills
        else:
            cv_skills = extract_skills_from_cv(cv_text)

        # Chặn đứng dây chuyền nếu JD nhập vào không có kỹ năng IT nào (VD: Nhập rác)
        if not jd_skills:
            state.tasks_db[task_id] = {"status": "failed", "message": "Không thể trích xuất kỹ năng từ JD này."}
            return

        # =====================================================================
        # BƯỚC 2: TÍNH TOÁN LỖ HỔNG (SKILL GAP ANALYSIS & NORMALIZATION)
        # Mục đích: Làm toán tập hợp để xem ứng viên thiếu kỹ năng gì, Level bao nhiêu.
        # =====================================================================
        gap_raw, matched = compute_skill_gap(cv_skills, jd_skills)
        
        # Nếu ứng viên đã quá giỏi (Không có Gap) -> Kết thúc sớm, vinh danh luôn.
        if not gap_raw:
            state.tasks_db[task_id] = {"status": "completed", "data": [], "message": "Ứng viên xuất sắc, CV đã cover 100% JD!"}
            return

        # --- Chuẩn hóa tên kỹ năng hổng (Alias Normalization) ---
        # Đưa các tên gọi lệch pha (VD: React.js, reactjs) về 1 tên chuẩn duy nhất để đi tìm Khóa học.
        search_gap_dict = {}
        for skill_key, gap_info in gap_raw.items():
            missing_lvls = gap_info["missing_levels"]
            
            # Xử lý nhánh bắt buộc (EXACT)
            if gap_info["match_mode"] == "EXACT":
                skill_name = gap_info.get("user_skill_name") or skill_key
                mapped_skill = clean_and_normalize(skill_name)
                search_gap_dict[mapped_skill] = missing_lvls
                
            # Xử lý nhánh tự chọn (ANY - VD: Biết 1 trong 3 ngôn ngữ Java/C#/Python)
            else:
                best_match = gap_info.get("user_best_match")
                if best_match:
                    match = re.match(r'([^\(]+)(?:\((.*)\))?', best_match)
                    if match:
                        main_skill = match.group(1).strip()
                        mapped_main = clean_and_normalize(main_skill)
                        search_gap_dict[mapped_main] = missing_lvls
                        if match.group(2):
                            sub_skills = [s.strip() for s in match.group(2).split(',')]
                            for sub in sub_skills:
                                mapped_sub = clean_and_normalize(sub)
                                search_gap_dict[mapped_sub] = missing_lvls

        # =====================================================================
        # BƯỚC 3: TRUY VẤN CÂY KHÓA HỌC (DFS TREE SEARCH)
        # Mục đích: Lao thẳng vào Két sắt (RAM) tìm các khóa học có dạy các kỹ năng bị hổng.
        # =====================================================================
        print(f"🌲 [TASK {task_id}] Đang lùng sục Cây Khóa Học...")
        # Lấy bản gốc của Cây Khóa học từ state
        candidate_courses_raw = dfs_tree_search(state.GLOBAL_COURSE_TREE, search_gap_dict)
        
        # Bộ lọc an toàn: Đảm bảo chỉ lấy các object dictionary, vứt bỏ string rác nếu có
        candidate_courses = []
        for c in candidate_courses_raw:
            if isinstance(c, dict):
                candidate_courses.append(c)

        if not candidate_courses:
            state.tasks_db[task_id] = {"status": "completed", "data": [], "message": "Không tìm thấy khóa học nào khớp với Gap."}
            return

        # =====================================================================
        # BƯỚC 4: CHẤM ĐIỂM SƯ PHẠM (LLM RANKING)
        # Mục đích: Nhờ AI đóng vai Giáo sư, duyệt rổ khóa học thô và chọn ra top lộ trình tốt nhất.
        # =====================================================================
        print(f"🏆 [TASK {task_id}] Đang gọi Qwen xếp hạng Tính Sư Phạm...")
        ranked_result = rank_courses_with_llm(candidate_courses, search_gap_dict, top_k=3)

        print(f"📦 [TASK {task_id}] Đang đóng gói dữ liệu Combo và Regular...")
        combo_courses = []
        regular_courses = []
        if isinstance(ranked_result, dict):
            combo_courses = ranked_result.get("combo_courses", [])
            regular_courses = ranked_result.get("regular_courses", [])
            
        # =====================================================================
        # BƯỚC 5: ĐO LƯỜNG VÀ ĐÁNH GIÁ (LIVE EVALUATION METRICS)
        # Mục đích: Tính toán các chỉ số Precision, Coverage theo thời gian thực để phục vụ chạy Benchmark.
        # =====================================================================
        try:
            from services.evaluator import log_live_evaluation_metrics
            log_live_evaluation_metrics(
                task_id=task_id, 
                recommended_list=regular_courses, 
                combo_list=combo_courses,
                candidate_pool=candidate_courses, 
                gap_dict=search_gap_dict
            )
        except Exception as eval_e:
            print(f"⚠️ Không thể in Metrics: {eval_e}")

        # =====================================================================
        # BƯỚC 6: CẬP NHẬT KẾT QUẢ VÀO KÉT SẮT (FINALIZATION)
        # Mục đích: Cất thành phẩm vào DB tạm để API Polling của Frontend (/task-status) chạy tới lấy.
        # =====================================================================
        state.tasks_db[task_id] = {
            "status": "completed", 
            "data": {
                "cv_skills": cv_skills,
                "jd_skills": jd_skills,
                "gap": gap_raw,
                "combo_courses": combo_courses,
                "regular_courses": regular_courses
            }, 
            "message": "Phân tích thành công!"
        }
        print(f"✅ [TASK {task_id}] HOÀN TẤT VÀ ĐÃ LƯU KẾT QUẢ VÀO CACHE.")
        
    except Exception as e:
        # Bắt lỗi toàn cục: Bất cứ khâu nào chết (LLM sập, đứt mạng...), Task sẽ được đánh dấu Failed an toàn.
        import traceback
        traceback.print_exc()
        print(f"❌ [TASK {task_id}] LỖI CRASH: {str(e)}")
        state.tasks_db[task_id] = {"status": "failed", "message": f"Lỗi hệ thống: {str(e)}"}