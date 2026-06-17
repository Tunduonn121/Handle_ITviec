import matplotlib.pyplot as plt
import numpy as np

# ==========================================
# 1. IMPORT DATA FROM BENCHMARK RESULTS (7 DATA POINTS)
# ==========================================
data_sizes = ['1K', '5K', '10K', '50K', '100K', '500K', '1M']

# --- EXECUTION TIME (SECONDS) ---
time_intersect_mean = [0.0022, 0.0061, 0.0080, 0.0509, 0.0987, 0.3925, 0.7693]
time_tree_mean = [0.0009, 0.0025, 0.0030, 0.0202, 0.0373, 0.1495, 0.3006]

time_intersect_std = [0.0002, 0.0020, 0.0005, 0.0065, 0.0072, 0.0109, 0.0251]
time_tree_std = [0.0002, 0.0008, 0.0002, 0.0045, 0.0029, 0.0052, 0.0156]

# --- RAM CONSUMPTION (MB) ---
ram_intersect_mean = [0.0058, 0.0297, 0.0535, 0.2777, 0.5629, 2.9272, 5.9341]
ram_tree_mean = [0.0020, 0.0092, 0.0186, 0.0962, 0.1951, 0.9015, 1.8275]

# ==========================================
# 2. DRAW CHARTS (WITH ERROR BARS)
# ==========================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

# --- CHART 1: EXECUTION TIME (Line Chart) ---
ax1.errorbar(data_sizes, time_intersect_mean, yerr=time_intersect_std, fmt='-o', 
             color='red', linewidth=2, capsize=4, capthick=2, ecolor='darkred',
             label='Set Intersection (Baseline)')

ax1.errorbar(data_sizes, time_tree_mean, yerr=time_tree_std, fmt='-s', 
             color='green', linewidth=2, capsize=4, capthick=2, ecolor='darkgreen',
             label='Tree Search (Proposed Architecture)')

ax1.set_title('Execution Time Curve (Average of 5 runs)', fontsize=14, fontweight='bold')
ax1.set_xlabel('Number of Courses in Database', fontsize=12)
ax1.set_ylabel('Execution Time (Seconds)', fontsize=12)
ax1.legend()
ax1.grid(True, linestyle='--', alpha=0.6)

for i, txt in enumerate(time_intersect_mean):
    ax1.annotate(f'{txt:.4f}s', (data_sizes[i], time_intersect_mean[i] + 0.02), color='darkred', fontsize=9, fontweight='bold')
for i, txt in enumerate(time_tree_mean):
    ax1.annotate(f'{txt:.4f}s', (data_sizes[i], time_tree_mean[i] - 0.035), color='darkgreen', fontsize=9, fontweight='bold')

# --- CHART 2: RAM CONSUMPTION (Bar Chart) ---
x_indexes = np.arange(len(data_sizes))
width = 0.35

rects1 = ax2.bar(x_indexes - width/2, ram_intersect_mean, width=width, color='salmon', edgecolor='darkred', label='Set Intersection')
rects2 = ax2.bar(x_indexes + width/2, ram_tree_mean, width=width, color='lightgreen', edgecolor='darkgreen', label='Tree Search')

ax2.set_title('Dynamic RAM Consumption (Peak Memory)', fontsize=14, fontweight='bold')
ax2.set_xlabel('Number of Courses in Database', fontsize=12)
ax2.set_ylabel('RAM (MB)', fontsize=12)
ax2.set_xticks(x_indexes)
ax2.set_xticklabels(data_sizes)
ax2.legend()
ax2.grid(True, linestyle='--', alpha=0.3, axis='y')

for i, val in enumerate(ram_intersect_mean):
    ax2.text(x_indexes[i] - width/2, val + 0.1, f'{val:.4f}', ha='center', color='darkred', fontsize=9, fontweight='bold', rotation=0)
for i, val in enumerate(ram_tree_mean):
    ax2.text(x_indexes[i] + width/2, val + 0.1, f'{val:.4f}', ha='center', color='darkgreen', fontsize=9, fontweight='bold', rotation=0)

# ==========================================
# 3. SAVE AND SHOW
# ==========================================
plt.tight_layout()
plt.savefig('benchmark_chart_v3_7_steps.png', dpi=300)
print("✅ Successfully saved the chart to: benchmark_chart_v3_7_steps.png")
plt.show()