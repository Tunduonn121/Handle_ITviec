import matplotlib.pyplot as plt
import numpy as np

# Set styling for IEEE 2-column format
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif", "Times New Roman", "serif"],
    "font.size": 9,
    "axes.labelsize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 9
})

def create_extraction_figure():
    # Figure size: 3.5 inches wide for single IEEE column, 2.4 inches tall
    fig, ax = plt.subplots(figsize=(3.5, 2.4))

    labels = ['Precision', 'Recall', 'F1']
    keyword_baseline = [84.1, 84.7, 84.4]
    llm_ours = [93.6, 100.0, 96.7]

    x = np.arange(len(labels))
    width = 0.35

    # Plot bars with grayscale-safe contrast and hatching
    rects1 = ax.bar(x - width/2, keyword_baseline, width, 
                    label='Keyword Baseline', 
                    color='#e0e0e0', edgecolor='black', hatch='//')
    
    rects2 = ax.bar(x + width/2, llm_ours, width, 
                    label='LLM (Ours)', 
                    color='#4d4d4d', edgecolor='black')

    # Formatting
    ax.set_ylabel('Percentage (%)')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 115) # Leave room above bars for values

    # Light gridline on Y axis only
    ax.grid(axis='y', linestyle='--', alpha=0.6)
    ax.set_axisbelow(True)

    # Legend above the chart to avoid overlapping tall bars
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.02), 
              ncol=2, frameon=False)

    # Function to attach text labels above bars
    def autolabel(rects, is_dark_bar=False):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height:.1f}',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom',
                        fontsize=8)

    autolabel(rects1)
    autolabel(rects2)

    # Save as tight vector PDF
    plt.savefig("fig_p1_extraction.pdf", bbox_inches="tight")
    print("Saved fig_p1_extraction.pdf")

if __name__ == "__main__":
    create_extraction_figure()