import argparse
import html
import random
from collections import Counter
from pathlib import Path
from typing import Callable

import agents.expectimax as exp_agent
import agents.mdp_agent as mdp_agent
import agents.simple_agents as simple_agents
import uno
from run import simulate_game

# ADD NEW AGENT IMPORTS HERE.
# Example after merging another branch:
# import agents.my_new_agent as my_new_agent


AgentFactory = tuple[str, Callable[[], uno.Player]]


def default_agent_factories(
    expectimax_depth: int,
    include_mdp: bool,
    mdp_sample_count: int,
    mdp_depth: int,
) -> list[AgentFactory]:
    """
    ADD FUTURE AGENTS IN THIS FUNCTION AFTER MERGING OTHER BRANCHES.

    Each factory must create a fresh player object. Reusing the same players
    across games would carry old hands into the next game.
    """
    factories: list[AgentFactory] = [
        ("Default", lambda: simple_agents.Default("Default")),
        ("Shuffle", lambda: simple_agents.Shuffle("Shuffle")),
        ("Power", lambda: simple_agents.Power("Power")),
        ("SimpleTree", lambda: simple_agents.SimpleTreeAgent("SimpleTree")),
        ("Weighted 1", lambda: simple_agents.WeightedHeuristicAgent1("Weighted 1")),
        ("Weighted 2", lambda: simple_agents.WeightedHeuristicAgent2("Weighted 2")),
        (
            "Expectimax",
            lambda: exp_agent.ExpectimaxAgent(
                "Expectimax",
                depth=expectimax_depth,
            ),
        ),
    ]

    # OPTIONAL MDP AGENT ENTRY.
    # This is behind --include-mdp because it may be slower than the simpler
    # agents. Remove the if-statement if you always want MDP in the graph.
    if include_mdp:
        factories.append(
            (
                "MDP",
                lambda: mdp_agent.MDPAgent(
                    "MDP",
                    sample_count=mdp_sample_count,
                    prediction_depth=mdp_depth,
                ),
            )
        )

    # ADD NEW MERGED AGENTS HERE.
    # Example:
    # factories.append(
    #     (
    #         "NewAgent",
    #         lambda: my_new_agent.NewAgent("NewAgent"),
    #     )
    # )

    return factories


def make_players(
    agent_factories: list[AgentFactory],
    rotation_offset: int,
) -> list[uno.Player]:
    players = [factory() for _, factory in agent_factories]

    if not players:
        return players

    rotation_offset = rotation_offset % len(players)
    return players[rotation_offset:] + players[:rotation_offset]


def run_games(
    game_count: int,
    agent_factories: list[AgentFactory],
    rotate_seats: bool,
) -> Counter[str]:
    wins: Counter[str] = Counter({name: 0 for name, _ in agent_factories})

    for game_index in range(game_count):
        rotation_offset = game_index if rotate_seats else 0
        players = make_players(agent_factories, rotation_offset)
        winner, _ = simulate_game(players, debug=False)
        wins[winner] += 1

    return wins


def run_experiment(
    game_counts: list[int],
    agent_factories: list[AgentFactory],
    rotate_seats: bool,
) -> dict[int, Counter[str]]:
    results: dict[int, Counter[str]] = {}

    for game_count in game_counts:
        print(f"Running {game_count} games...")
        results[game_count] = run_games(game_count, agent_factories, rotate_seats)

    return results


def print_results(
    results: dict[int, Counter[str]],
    agent_names: list[str],
) -> None:
    print("\nWin counts:\n")
    header = "Games".ljust(8) + "".join(name.rjust(14) for name in agent_names)
    print(header)
    print("-" * len(header))

    for game_count, wins in results.items():
        row = str(game_count).ljust(8)
        for agent_name in agent_names:
            row += f"{wins[agent_name]:>14}"
        print(row)

    print("\nWin proportions:\n")
    print(header)
    print("-" * len(header))

    for game_count, wins in results.items():
        row = str(game_count).ljust(8)
        for agent_name in agent_names:
            proportion = wins[agent_name] / game_count
            row += f"{proportion:>13.1%} "
        print(row)

    timed_out_games = sum(wins.get("Timed Out", 0) for wins in results.values())
    if timed_out_games:
        print(f"\nTimed out games: {timed_out_games}")

def write_svg_results(
    results: dict[int, Counter[str]],
    agent_names: list[str],
    output_path: Path,
) -> None:
    game_counts = list(results.keys())
    colors = [
        "#2563eb", "#dc2626", "#16a34a", "#ca8a04", "#7c3aed",
        "#0891b2", "#db2777", "#ea580c", "#475569", "#65a30d",
    ]

    chart_left = 88
    chart_top = 58
    chart_height = 320
    group_width = 96
    chart_width = len(game_counts) * group_width
    width = max(820, chart_left + chart_width + 260)
    height = 520
    bar_width = max(3, min(12, int((group_width * 0.72) / max(len(agent_names), 1))))

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="28" y="34" font-family="Arial" font-size="22" font-weight="700">UNO Agent Win Proportions</text>',
    ]

    for tick in range(6):
        value = tick / 5
        y = chart_top + chart_height - value * chart_height
        lines.append(f'<line x1="{chart_left}" y1="{y}" x2="{chart_left + chart_width}" y2="{y}" stroke="#e5e7eb"/>')
        lines.append(f'<text x="{chart_left - 12}" y="{y + 4}" font-family="Arial" font-size="12" text-anchor="end">{int(value * 100)}%</text>')

    lines.append(f'<line x1="{chart_left}" y1="{chart_top}" x2="{chart_left}" y2="{chart_top + chart_height}" stroke="#111827"/>')
    lines.append(f'<line x1="{chart_left}" y1="{chart_top + chart_height}" x2="{chart_left + chart_width}" y2="{chart_top + chart_height}" stroke="#111827"/>')

    for group_index, game_count in enumerate(game_counts):
        group_x = chart_left + group_index * group_width + group_width / 2
        first_bar_x = group_x - (bar_width * len(agent_names)) / 2

        for agent_index, agent_name in enumerate(agent_names):
            wins = results[game_count][agent_name]
            proportion = wins / game_count
            bar_height = proportion * chart_height
            x = first_bar_x + agent_index * bar_width
            y = chart_top + chart_height - bar_height
            color = colors[agent_index % len(colors)]
            label = html.escape(f"{agent_name}: {wins}/{game_count} ({proportion:.1%})")

            lines.append("<g>")
            lines.append(f"<title>{label}</title>")
            lines.append(f'<rect x="{x}" y="{y}" width="{bar_width - 1}" height="{bar_height}" fill="{color}"/>')
            lines.append("</g>")

        lines.append(f'<text x="{group_x}" y="{chart_top + chart_height + 24}" font-family="Arial" font-size="12" text-anchor="middle">{game_count}</text>')

    legend_x = chart_left + chart_width + 34
    for agent_index, agent_name in enumerate(agent_names):
        y = chart_top + agent_index * 24
        color = colors[agent_index % len(colors)]
        lines.append(f'<rect x="{legend_x}" y="{y - 11}" width="12" height="12" fill="{color}"/>')
        lines.append(f'<text x="{legend_x + 20}" y="{y}" font-family="Arial" font-size="13">{html.escape(agent_name)}</text>')

    lines.append("</svg>")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nSaved SVG graph to {output_path}")

def plot_results(
    results: dict[int, Counter[str]],
    agent_names: list[str],
    output_path: Path,
    show_plot: bool,
) -> None:
    if output_path.suffix.lower() == ".svg":
        write_svg_results(results, agent_names, output_path)
        return

    try:
        import matplotlib.pyplot as plt
        from matplotlib.ticker import PercentFormatter
    except ImportError:
        fallback_path = output_path.with_suffix(".svg")
        print("matplotlib is not installed, so saving a built-in SVG graph instead.")
        write_svg_results(results, agent_names, fallback_path)
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run UNO agent matchups and graph win proportions.",
    )
    parser.add_argument(
        "--games",
        nargs="+",
        type=int,
        default=[100, 250, 500],
        help="Sample sizes to run and graph.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("agent_win_rates.svg"),
        help="Where to save the generated graph. Use .svg to avoid extra dependencies.",
    )
    parser.add_argument(
        "--expectimax-depth",
        type=int,
        default=2,
        choices=[1, 2, 3],
        help="Expectimax search depth.",
    )
    parser.add_argument(
        "--include-mdp",
        action="store_true",
        help="Include the current MDP agent in the matchup.",
    )
    parser.add_argument(
        "--mdp-samples",
        type=int,
        default=3,
        help="Number of samples for each MDP prediction.",
    )
    parser.add_argument(
        "--mdp-depth",
        type=int,
        default=2,
        help="Prediction depth for the MDP agent.",
    )
    parser.add_argument(
        "--no-rotate",
        action="store_true",
        help="Keep agents in the same seat order every game.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible runs.",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Open a matplotlib window after saving the graph.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    agent_factories = default_agent_factories(
        expectimax_depth=args.expectimax_depth,
        include_mdp=args.include_mdp,
        mdp_sample_count=args.mdp_samples,
        mdp_depth=args.mdp_depth,
    )
    agent_names = [name for name, _ in agent_factories]

    results = run_experiment(
        game_counts=args.games,
        agent_factories=agent_factories,
        rotate_seats=not args.no_rotate,
    )

    print_results(results, agent_names)
    plot_results(results, agent_names, args.output, args.show)


if __name__ == "__main__":
    main()
