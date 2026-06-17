import matplotlib.pyplot as plt
import numpy as np

# ==========================================
# NHẬP SỐ LIỆU SẾP ĐÃ ĐẾM ĐƯỢC VÀO ĐÂY
# ==========================================
# Tên 5 tiêu chí đánh giá
criteria = [
    'Disjunctive\nClause (A or B)', 
    'Nested Group\nParsing', 
    'Level\nQuantification', 
    'Zero-Hallucination', 
    'JSON Schema\nSuccess'
]

# Phần trăm của thuật toán Keyword cũ (Baseline)
# Dữ liệu thực tế 45 Test cases: Không gom được ANY (0%), Bóc ngoặc đúng ngẫu nhiên 2 câu (4.4%), Không có Level (0%), Không sinh ảo giác do dùng từ điển tĩnh (100%), Chuẩn JSON (100%)
baseline_scores = [0.0, 4.4, 0.0, 100.0, 100.0]

# Phần trăm của Hybrid LLM (Qwen-480B)
# Dữ liệu thực tế 45 Test cases: Gom ANY xuất sắc (97.7%), Bóc ngoặc (95.5%), Level (93.3%), Lọt một vài soft-skills (91.1%), Parse JSON thành công tuyệt đối (100.0%)
llm_scores = [97.7, 95.5, 93.3, 91.1, 100.0]
# ==========================================
# VẼ BIỂU ĐỒ (SẾP KHÔNG CẦN SỬA ĐOẠN NÀY)
# ==========================================
x = np.arange(len(criteria))  # Vị trí các nhãn trên trục x
width = 0.35  # Độ rộng của cột

fig, ax = plt.subplots(figsize=(10, 6))

# Vẽ 2 nhóm cột
rects1 = ax.bar(x - width/2, baseline_scores, width, label='Keyword Matching (Baseline)', color='#e74c3c')
rects2 = ax.bar(x + width/2, llm_scores, width, label='Hybrid LLM (Proposed)', color='#2ecc71')

# Trang trí biểu đồ
ax.set_ylabel('Accuracy Score (%)', fontweight='bold')
ax.set_title('Performance Comparison: Skill Extraction Engine', fontweight='bold', pad=20)
ax.set_xticks(x)
ax.set_xticklabels(criteria, fontsize=10)
ax.set_ylim(0, 115) # Nới rộng trục Y để hiển thị số % không bị lẹm
ax.legend(loc='upper left')
ax.grid(axis='y', linestyle='--', alpha=0.7)

# Gắn nhãn số liệu lên đầu mỗi cột
def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{height}%',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # Dịch lên 3 points
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

autolabel(rects1)
autolabel(rects2)

fig.tight_layout()

# Lưu thành file ảnh độ phân giải cao để nhúng vào Word
plt.savefig('extraction_benchmark_chart.png', dpi=300)
print("✅ Đã tạo thành công file ảnh: extraction_benchmark_chart.png")
plt.show()