"""
Ground Statistics Generator

Reads the match stats CSV and generates:
1. A summary table of match duration by ground
2. A CSV file with aggregated stats
3. A bar chart visualization (if matplotlib is available)
"""

import csv
import re
from collections import defaultdict

# Try to import matplotlib for chart generation (optional)
try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


def load_data():
    """
    Load match data from CSV and group by ground.

    Returns a dictionary where:
    - Key: ground name
    - Value: list of match durations (in minutes)
    """
    grounds = defaultdict(list)

    with open('arcl_match_stats.csv', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            dur = row['match_duration']
            ground = row['ground']

            # Only include matches with both duration and ground
            if dur and ground:
                # Extract the number from "123 min"
                m = re.search(r'(\d+)', dur)
                if m:
                    grounds[ground].append(int(m.group(1)))

    return grounds


def build_stats(grounds):
    """
    Calculate statistics for each ground.

    Returns a list of dictionaries with:
    - ground: name
    - matches: count of matches
    - avg_duration: average match duration
    - min_duration: shortest match
    - max_duration: longest match
    """
    stats = []

    for ground, durations in grounds.items():
        stats.append({
            'ground': ground,
            'matches': len(durations),
            'avg_duration': round(sum(durations) / len(durations)),
            'min_duration': min(durations),
            'max_duration': max(durations),
        })

    # Sort by number of matches (most first)
    stats.sort(key=lambda x: -x['matches'])
    return stats


def write_csv(stats):
    """Save aggregated stats to CSV file."""
    with open('ground_stats.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=['ground', 'matches', 'avg_duration', 'min_duration', 'max_duration']
        )
        writer.writeheader()
        writer.writerows(stats)

    print("Saved ground_stats.csv")


def create_chart(stats):
    """
    Create a bar chart showing match duration by ground.

    The chart shows:
    - Average duration as the bar height
    - Min/max range as error bars
    - Match count labeled above each bar
    """
    if not HAS_MATPLOTLIB:
        print("matplotlib not available, skipping chart generation")
        print("Install with: pip install matplotlib")
        return

    # Shorten ground names for display
    def shorten(name):
        name = name.replace('Softball Field', 'SF')
        name = name.replace('Field', 'F')
        name = name.replace('Park', 'Pk')
        name = name.replace('Pitch', 'P')
        return name

    labels = [shorten(s['ground']) for s in stats]
    matches = [s['matches'] for s in stats]
    avgs = [s['avg_duration'] for s in stats]
    mins = [s['min_duration'] for s in stats]
    maxs = [s['max_duration'] for s in stats]

    fig, ax1 = plt.subplots(figsize=(16, 9))

    x = range(len(stats))
    bar_width = 0.6

    # Calculate error bar ranges (distance from avg to min/max)
    lower_err = [a - mn for a, mn in zip(avgs, mins)]
    upper_err = [mx - a for a, mx in zip(avgs, maxs)]

    # Create bar chart
    bars = ax1.bar(x, avgs, bar_width, color='#2196F3', alpha=0.85, label='Avg Duration (min)')

    # Add error bars showing min-max range
    ax1.errorbar(
        x, avgs,
        yerr=[lower_err, upper_err],
        fmt='none',
        ecolor='#333333',
        elinewidth=1.5,
        capsize=5,
        capthick=1.5,
        label='Min-Max Range'
    )

    # Add match count labels on top of bars
    for i, (bar, count) in enumerate(zip(bars, matches)):
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(upper_err) * 0.05,
            f'{count} matches',
            ha='center',
            va='bottom',
            fontsize=8,
            fontweight='bold',
            color='#333'
        )

    # Labels and formatting
    ax1.set_xlabel('Ground', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Match Duration (minutes)', fontsize=12, fontweight='bold')
    ax1.set_title('ARCL Match Duration by Ground\n(Avg, Min, Max with Match Count)', fontsize=14, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    ax1.legend(loc='upper right', fontsize=10)
    ax1.grid(axis='y', alpha=0.3)
    ax1.set_ylim(0, max(maxs) * 1.15)

    plt.tight_layout()
    plt.savefig('ground_stats_chart.png', dpi=150, bbox_inches='tight')
    print("Saved ground_stats_chart.png")
    plt.close()


def print_table(stats):
    """Print a formatted table to the console."""
    print(f"\n{'Ground':<50} {'Matches':>8} {'Avg (min)':>10} {'Min (min)':>10} {'Max (min)':>10}")
    print("-" * 92)

    for s in stats:
        print(f"{s['ground']:<50} {s['matches']:>8} {s['avg_duration']:>10} {s['min_duration']:>10} {s['max_duration']:>10}")

    print("-" * 92)

    # Calculate totals
    total_matches = sum(s['matches'] for s in stats)
    weighted_avg = round(
        sum(s['avg_duration'] * s['matches'] for s in stats) / total_matches
    )
    print(f"{'TOTAL':<50} {total_matches:>8} {weighted_avg:>10}")


def main():
    # Load and process data
    grounds = load_data()
    stats = build_stats(grounds)

    # Output results
    print_table(stats)
    write_csv(stats)
    create_chart(stats)


if __name__ == '__main__':
    main()
