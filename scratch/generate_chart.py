import os
import sys
import subprocess

# Ensure matplotlib is installed
try:
    import matplotlib.pyplot as plt
except ImportError:
    print("matplotlib not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "matplotlib"])
    import matplotlib.pyplot as plt

def generate_missing_data_chart():
    # Data from cleaning_log.txt
    columns = [
        'easement', 
        'apartment_number', 
        'SALE PRICE PER SQFT', 
        'SQFT_PER_UNIT', 
        'land_sqft', 
        'gross_sqft'
    ]
    missing_rates = [100.00, 75.32, 52.48, 52.43, 52.26, 52.26]
    
    # Sort data for horizontal bar chart
    data = sorted(zip(columns, missing_rates), key=lambda x: x[1])
    sorted_cols, sorted_rates = zip(*data)

    # Style configuration
    fig, ax = plt.subplots(figsize=(6.5, 4.5), dpi=300)
    fig.patch.set_alpha(0.0) # Transparent background
    ax.patch.set_alpha(0.0)

    # Colors: Amber/Orange for warning alert, matching blue accent
    colors = ['#F59E0B' if rate > 50 else '#3B82F6' for rate in sorted_rates]
    
    bars = ax.barh(sorted_cols, sorted_rates, color=colors, height=0.55)

    # Axis formatting
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#94A3B8')
    ax.spines['bottom'].set_color('#94A3B8')
    ax.tick_params(colors='#1E293B', labelsize=10)
    ax.set_xlabel('Tỷ lệ khuyết thiếu (%)', fontsize=11, color='#1E293B', fontweight='bold', labelpad=10)
    ax.set_title('Tỷ lệ trống của 6 cột bị loại bỏ (>50%)', fontsize=12, color='#1E293B', fontweight='bold', pad=15)
    ax.set_xlim(0, 110)

    # Add value labels to the end of each bar
    for bar in bars:
        width = bar.get_width()
        ax.text(
            width + 2, 
            bar.get_y() + bar.get_height()/2, 
            f'{width:.1f}%', 
            ha='left', 
            va='center', 
            fontsize=10, 
            fontweight='bold',
            color='#EF4444' if width > 50 else '#1E293B'
        )

    plt.tight_layout()
    out_dir = r"d:\Profile\Visual Code File\DATN_DP02_NYC\data\data clean"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "missing_data_chart.png")
    plt.savefig(out_path, transparent=True, bbox_inches='tight')
    print(f"Chart saved successfully to: {out_path}")

if __name__ == "__main__":
    generate_missing_data_chart()
