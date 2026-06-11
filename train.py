import copy
import multiprocessing
import random

from agents import mdp_agent
from agents import simple_agents
import uno

# Configuration options for modeling evolution.
POPULATION_SIZE = 20
GENERATIONS = 50
GAMES_PER_EVAL = 300
MUTATION_RATE = 0.5

# Generates a set of random parameters for reward + penalty tuning.
def random_params() -> dict:
    return {
        "survival_reward": random.randint(5, 150),
        "draw_penalty": random.randint(-200, -20),
        "win_reward": random.randint(50, 500),
        "loss_penalty": random.randint(-500, -50),
        "hand_size_penalty": random.randint(-10, -1),
        "lowest_opponent_hand_size_reward": random.randint(1, 100),
    }

# Slightly mutate the given parameters.
def mutate(params: dict) -> dict:
    mutated_params = copy.copy(params)
    for key in mutated_params:
        if random.random() < MUTATION_RATE:
            scale = max(1, abs(int(mutated_params[key] * 0.2)))
            mutated_params[key] += random.randint(-scale, scale)
            
    return mutated_params

# Simulates one game with three Default agents and an MDP
# agent given the input parameters as reward values.
def simulate_game(params: dict) -> str:
    players = [
        simple_agents.Default("Default 1"),
        simple_agents.Default("Default 2"),
        simple_agents.Default("Default 3"),
        mdp_agent.MDPAgent("MDP", **params),
    ]
    random.shuffle(players)

    # Similar behavior as simulate_game() in run.py.
    game_state = uno.GameState(players, False)
    while True:
        if game_state.turn_counter > 10000:
            return "Timed Out"
        
        current_player = game_state.process_turn()
        if game_state.game_end:
            return current_player.name

# Simulates one game with the gtiven parameters and returns 
# a 1 if the parameters led to a winning outcome.
def run_game(params: dict) -> int:
    random.seed()
    return 1 if simulate_game(params) == "MDP" else 0

# Trains a set of MDP agent parameters by calculating the highest
# performing set of criteria and then slightly modifying them 
# to mimic natural selection, hopefully leading to a near-optimal MDP agent.
def train(debug: bool = False):
    # Establish a population set of random parameters for the initial set.
    population = [random_params() for _ in range(POPULATION_SIZE)]
    
    # Store the best agent score and their parameters across all generations.
    best_ever = None
    best_ever_score = 0.0

    for generation in range(GENERATIONS):
        all_params = [params for params in population for _ in range(GAMES_PER_EVAL)]

        # Multithreading. Yay!.
        with multiprocessing.Pool() as pool:
            all_results = pool.map(run_game, all_params)

        # Aggregate results back into per-individual win rates.
        scored = []
        for i, params in enumerate(population):
            chunk = all_results[i * GAMES_PER_EVAL:(i + 1) * GAMES_PER_EVAL]
            win_rate = sum(chunk) / GAMES_PER_EVAL
            scored.append((params, win_rate))

        # Select the highest performance parameter set from the 
        # entire space and check to see if it is the highest performer.
        scored.sort(key=lambda x: x[1], reverse=True)
        best_params, best_score = scored[0]

        if best_score > best_ever_score:
            best_ever_score = best_score
            best_ever = copy.copy(best_params)

        if debug:
            print(f"Gen {generation:02d}: best = {best_score:.2f} | all-time best = {best_ever_score:.2f} | {best_params}")

        # Neext generation consists of half survivors, half mutants
        survivors = [params for params, _ in scored[:POPULATION_SIZE // 2]]
        mutants = [mutate(random.choice(survivors)) for _ in range(POPULATION_SIZE // 2 - 1)]
        population = [best_params] + survivors + mutants

    print("\nBest params found:")
    print(best_ever)
    return best_ever

if __name__ == "__main__":
    multiprocessing.freeze_support()
    train()