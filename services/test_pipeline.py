import json
import time

# Import các hàm từ 2 file Sếp vừa hoàn thiện
# (Giả sử 2 file của Sếp đang nằm trong thư mục 'services')
from skill_extractor import extract_skills_from_jd, extract_skills_from_cv
from skill_gap_calculator import compute_skill_gap, get_gap_summary

def _safe_token_match(a: str, b: str) -> bool:
    """Khớp an toàn: bằng nhau, hoặc a là 1 token/cụm độc lập trong b (không cắt giữa từ)."""
    a, b = a.strip().lower(), b.strip().lower()
    if a == b:
        return True
    # word-boundary tự chế, an toàn cho c#, c++, .net
    pat = r'(?<![a-z0-9])' + re.escape(a) + r'(?![a-z0-9])'
    return re.search(pat, b) is not None

def run_e2e_test():
    print("="*80)
    print("🚀 BẮT ĐẦU TEST LIÊN HOÀN (END-TO-END PIPELINE) 🚀")
    print("="*80)

    # 1. DỮ LIỆU ĐẦU VÀO (RAW TEXT)
    sample_jd = """
    VỊ TRÍ: SENIOR BACKEND ENGINEER (FINTECH)
    
    [YÊU CẦU BẮT BUỘC]
    - Tối thiểu 4 năm kinh nghiệm làm việc với: C#, .NET 8, SQL Server.
    - Thành thạo ít nhất một trong các nhóm sau:
      * Java (Spring Boot, Hibernate, Microservices)
      * Node.js (ExpressJS, NestJS)
      * Python (Django, FastAPI)
    - Kỹ năng về các loại CSDL MySQL, PostgreSQL/Oracle, MongoDB, Redis.
    - Có kinh nghiệm thiết kế RESTful API, gRPC hoặc GraphQL.
    
    [NICE TO HAVE (ƯU TIÊN)]
    - Từng làm việc với hệ thống Cloud AWS, Azure or GCP.
    - Kinh nghiệm triển khai Kubernetes và Docker là một lợi thế rất lớn.
    - CI/CD (Gitlab CI, Jenkins).
    """

    sample_cv = """
    DƯƠNG NGUYỄN - BACKEND DEVELOPER
    
    KINH NGHIỆM:
    - 5 năm kinh nghiệm Java, thành thạo Spring Boot, Microservices. Chưa biết Hibernate.
    - 3 năm làm việc với MySQL, PostgreSQL
    - Có hiểu biết về REST API.
    - Kinh nghiệm triển khai Docker (2 năm), Kubernetes (1 năm)
    - Sử dụng thành thạo CI/CD qua Jenkins
    - Biết sơ qua Python và Node.js nhưng chưa dùng Framework.
    """

    # 2. GỌI AI BÓC TÁCH (EXTRACTION)
    print("\n⏳ [1/4] Đang gọi AI (Ollama) bóc tách JD...")
    start_time = time.time()
    jd_skills_json = extract_skills_from_jd(sample_jd)
    print(f"✅ Xong JD (Mất {round(time.time() - start_time, 2)}s)")

    print("\n⏳ [2/4] Đang gọi AI (Ollama) bóc tách CV...")
    start_time = time.time()
    cv_skills_json = extract_skills_from_cv(sample_cv)
    print(f"✅ Xong CV (Mất {round(time.time() - start_time, 2)}s)")

    # 3. CHẠY THUẬT TOÁN TÍNH GAP (MATCHING)
    print("\n⏳ [3/4] Đang đưa JSON vào Máy nghiền Thuật toán tính Gap...")
    gap, matched = compute_skill_gap(cv_skills_json, jd_skills_json)
    summary = get_gap_summary(gap)
    print("✅ Đã tính toán xong!\n")

    # 4. IN BÁO CÁO TỔNG KẾT
    print("="*80)
    print("🎯 KẾT QUẢ PHÂN TÍCH HỒ SƠ 🎯")
    print("="*80)

    print("\n🟢 1. CÁC KỸ NĂNG ĐÃ ĐÁP ỨNG XUẤT SẮC:")
    for skill, info in matched.items():
        if info.get('match_mode') == 'ANY_COMPLEX':
            print(f"  ✅ Nhóm {skill[:20]}... -> {info['status']}")
        elif info.get('match_mode') == 'ANY':
            print(f"  ✅ Nhóm {skill} -> Đã pass nhờ '{info.get('user_best_match')}' (Lvl {info.get('user_level')})")
        else:
            print(f"  ✅ {skill} -> Đạt Lvl {info.get('user_level')}")

    print("\n🚨 2. CÁC KỸ NĂNG CẦN HỌC BỔ SUNG (SKILL GAP):")
    if summary["critical"]:
        print("\n  🔴 CRITICAL (Bắt buộc Level 3):")
        for item in summary["critical"]:
            print(f"    - {item['recommendation']} ⏱️ ({item['hours_estimate']}h)")
            
    if summary["important"]:
        print("\n  🟡 IMPORTANT (Level 2):")
        for item in summary["important"]:
            print(f"    - {item['recommendation']} ⏱️ ({item['hours_estimate']}h)")
            
    if summary["nice_to_have"]:
        print("\n  🔵 NICE TO HAVE (Level 1):")
        for item in summary["nice_to_have"]:
            print(f"    - {item['recommendation']} ⏱️ ({item['hours_estimate']}h)")

    print(f"\n⏱️ TỔNG THỜI GIAN CẦN ĐỂ LẤY JOB NÀY: {summary['total_hours_estimate']} giờ học")
    print("="*80)

if __name__ == "__main__":
    run_e2e_test()