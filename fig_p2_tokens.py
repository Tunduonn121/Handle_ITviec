import matplotlib.pyplot as plt

# Set styling for IEEE 2-column format
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif", "Times New Roman", "serif"],
    "font.size": 9,
    "axes.labelsize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8
})

def create_tokens_figure():
    # Figure size: 3.5 inches wide, 2.5 inches tall
    fig, ax = plt.subplots(figsize=(3.5, 2.5))

    labels = ['Naive\n(All Courses)', 'Filter-only', 'Tree + Filter\n(Full Pipeline)']
    values = [434029, 1052, 1052]

    # Use a consistent, dark gray for all bars (contrast comes from background)
    bars = ax.bar(labels, values, color='#4d4d4d', edgecolor='black', width=0.5)

    # Formatting for Log Scale
    ax.set_yscale('log')
    ax.set_ylabel('Tokens per query (log scale)')
    
    # Set y-limits to give headroom for the text label above the highest bar
    ax.set_ylim(bottom=100, top=3_000_000)

    # Light gridline on Y axis only
    ax.grid(axis='y', linestyle='--', alpha=0.6, which='major')
    ax.set_axisbelow(True)

    # Attach text labels above bars
    for bar in bars:
        height = bar.get_height()
        # For log scale, multiply by a factor (e.g., 1.4) to shift text up linearly on the visual axis
        text_y = height * 1.4 
        ax.text(bar.get_x() + bar.get_width() / 2, text_y,
                f'{int(height):,}',  # Format with thousands comma separator
                ha='center', va='bottom',
                fontsize=8)

    # Remove the top and right spines for a cleaner academic look
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Save as tight vector PDF
    plt.savefig("fig_p2_tokens.pdf", bbox_inches="tight")
    print("Saved fig_p2_tokens.pdf")

if __name__ == "__main__":
    create_tokens_figure()