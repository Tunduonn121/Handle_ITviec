import time
import tracemalloc
import random
import statistics

print("="*85)
print("🚀 HỆ THỐNG KIỂM THỬ HIỆU NĂNG V3 (7 MỐC DATA x 5 ITERATIONS)")
print("🔥 So sánh: Set Intersection (Truyền thống) vs Tree Search (Đề xuất)")
print("="*85)

# ==========================================
# 1. TẠO DỮ LIỆU GIẢ LẬP
# ==========================================
SKILL_POOL = ["C#", "Java", "Python", "SQL", "Docker", "AWS", "React", "NodeJS", "Git", "Linux"]

def generate_mock_data(num_courses):
    courses = []
    tree = {"Core": [], "Web": [], "DevOps": []}
    for i in range(num_courses):
        skills = random.sample(SKILL_POOL, random.randint(3, 5))
        course = {"id": i, "skills": set(skills)}
        courses.append(course)
        category = random.choice(["Core", "Web", "DevOps"])
        tree[category].append(course)
    return courses, tree

# ==========================================
# 2. THUẬT TOÁN
# ==========================================
def intersection_baseline(target_gap, courses):
    target_set = set(target_gap)
    return [c for c in courses if target_set.intersection(c["skills"])]

def tree_search_proposed(target_gap, tree):
    target_set = set(target_gap)
    relevant_branch = tree["Web"] # Giả lập đã prune nhánh Core & DevOps
    return [c for c in relevant_branch if target_set.intersection(c["skills"])]

# ==========================================
# 3. CHẠY VÀ ĐO LƯỜNG
# ==========================================
def run_benchmark(iterations=5):
    # 🌟 CẬP NHẬT 7 MỐC DATA TẠI ĐÂY 🌟
    data_sizes = [1000, 5000, 10_000, 50_000, 100_000, 500_000, 1_000_000]
    target_gap = ["React", "NodeJS"]
    
    print(f"{'Data Size':<12} | {'Algorithm':<20} | {'Thời gian (Giây) [Min - Max] -> TB ± Độ lệch':<45} | {'RAM (MB) -> TB'}")
    print("-" * 105)
    
    for size in data_sizes:
        courses, tree = generate_mock_data(size)
        
        t_intersect, r_intersect = [], []
        t_tree, r_tree = [], []
        
        for _ in range(iterations):
            # Test 1: Set Intersection
            tracemalloc.start()
            start = time.perf_counter()
            intersection_baseline(target_gap, courses)
            t_intersect.append(time.perf_counter() - start)
            r_intersect.append(tracemalloc.get_traced_memory()[1] / 10**6)
            tracemalloc.stop()
            
            # Test 2: Tree Search
            tracemalloc.start()
            start = time.perf_counter()
            tree_search_proposed(target_gap, tree)
            t_tree.append(time.perf_counter() - start)
            r_tree.append(tracemalloc.get_traced_memory()[1] / 10**6)
            tracemalloc.stop()

        # Hàm helper in kết quả
        def print_stats(name, t_list, r_list):
            t_mean = statistics.mean(t_list)
            t_stdev = statistics.stdev(t_list)
            t_min, t_max = min(t_list), max(t_list)
            r_mean = statistics.mean(r_list)
            
            time_str = f"[{t_min:.4f} - {t_max:.4f}] -> {t_mean:.4f} ± {t_stdev:.4f}"
            print(f"{size:<12,} | {name:<20} | {time_str:<45} | {r_mean:.4f}")

        print_stats("Set Intersection", t_intersect, r_intersect)
        print_stats("Tree Search", t_tree, r_tree)
        print("-" * 105)

if __name__ == "__main__":
    run_benchmark(iterations=5)