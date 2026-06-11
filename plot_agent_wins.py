import argparse
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
        # ADD OR REMOVE BASELINE AGENTS HERE.
        #
        # Format:
        # ("Graph Label", lambda: agent_module.AgentClass("In-Game Name")),
        #
        # The graph label and in-game name should usually match, because
        # simulate_game returns the winner's in-game name.
        ("Default", lambda: simple_agents.Default("Default")),
        ("Power", lambda: simple_agents.Power("Power")),
        ("SimpleTree", lambda: simple_agents.SimpleTreeAgent("SimpleTree")),

        # EXPECTIMAX AGENT ENTRY.
        # Modify this if you want to compare multiple depths, for example:
        # ("Expectimax d1", lambda: exp_agent.ExpectimaxAgent("Expectimax d1", depth=1)),
        # ("Expectimax d2", lambda: exp_agent.ExpectimaxAgent("Expectimax d2", depth=2)),
        # ("Expectimax d3", lambda: exp_agent.ExpectimaxAgent("Expectimax d3", depth=3)),
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
    print("\nWin proportions:\n")
    header = "Games".ljust(8) + "".join(name.rjust(14) for name in agent_names)
    print(header)
    print("-" * len(header))

    for game_count, wins in results.items():
        row = str(game_count).ljust(8)
        for agent_name in agent_names:
            proportion = wins[agent_name] / game_count
            row += f"{proportion:>13.1%} "
        print(row)


def plot_results(
    results: dict[int, Counter[str]],
    agent_names: list[str],
    output_path: Path,
    show_plot: bool,
) -> None:
    try:
        import matplotlib.pyplot as plt
        from matplotlib.ticker import PercentFormatter
    except ImportError as error:
        raise SystemExit(
            "matplotlib is required to graph results. Install it with "
            "`pip install matplotlib` and run this script again."
        ) from error

    game_counts = list(results.keys())
    x_positions = list(range(len(game_counts)))
    bar_width = min(0.8 / max(len(agent_names), 1), 0.18)
    first_bar_offset = -bar_width * (len(agent_names) - 1) / 2

    fig, ax = plt.subplots(figsize=(11, 6))

    for agent_index, agent_name in enumerate(agent_names):
        proportions = [
            results[game_count][agent_name] / game_count
            for game_count in game_counts
        ]
        positions = [
            x + first_bar_offset + agent_index * bar_width
            for x in x_positions
        ]
        ax.bar(positions, proportions, width=bar_width, label=agent_name)

    ax.set_title("UNO Agent Win Proportions")
    ax.set_xlabel("Games played")
    ax.set_ylabel("Win proportion")
    ax.set_xticks(x_positions)
    ax.set_xticklabels([str(game_count) for game_count in game_counts])
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.set_ylim(0, 1)
    ax.grid(axis="y", alpha=0.25)
    ax.legend()

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    print(f"\nSaved graph to {output_path}")

    if show_plot:
        plt.show()


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
        default=Path("agent_win_rates.png"),
        help="Where to save the generated graph.",
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
