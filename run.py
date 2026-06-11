import random

import agents.expectimax as exp_agent
import agents.mdp_agent as mdp_agent
import agents.simple_agents as simple_agents
import agents.user_agent as user_agent
import uno

# Simulates one game with default player behavior.
def simulate_game(
    players: list[uno.Player] = 
        [simple_agents.Default("Player 1"), 
         simple_agents.Default("Player 2"), 
         simple_agents.Default("Player 3"), 
         simple_agents.Default("Player 4")],
    debug: bool = False) -> tuple[str, int]:
    
    random.shuffle(players)
    game_state: uno.GameState = uno.GameState(players, debug)

    while True:
        if game_state.turn_counter > 10000:
            return ("Timed Out", game_state.turn_counter)
        
        current_player: uno.Player = game_state.process_turn()
        
        if game_state.game_end:
            if debug:
                print(f"{current_player.name} wins!")
                print(f"Game ended in {game_state.turn_counter} turns.")
                
            return (current_player.name, game_state.turn_counter)
        
# Runs "n" games of UNO using simulate_game(),
def simulate_many_games(n: int, players: list[uno.Player], debug: bool = False) -> None:
    game_results: list[tuple[str, int]] = []
    
    for i in range(0, n):
        print(f"Game {i + 1}")
        game_results.append(simulate_game(players, debug))
        
    print("Player Wins:\n")
    player_wins = {}
    for result in game_results:
        player_wins[result[0]] = player_wins.get(result[0], 0) + 1
        
    # Sorts in descending order of wins.
    max_ratio = 0
    win_counts = sorted(player_wins.items(), key=lambda element: element[1], reverse=True)
    for player, wins in win_counts:
        max_ratio = wins / n
        print(f"{player}: {wins}")
        print(f"{player} won: {max_ratio:.2%} of games")
        print()

if __name__ == "__main__":
    players = []
    players.append(user_agent.UserAgent("User"))
    players.append(simple_agents.Default("First-in-first-out"))
    players.append(simple_agents.Shuffle("Shuffle"))
    players.append(simple_agents.Power("Power"))
    players.append(simple_agents.Wait("Wait"))
    players.append(simple_agents.SimpleTreeAgent("Tree Agent"))
    players.append(simple_agents.WeightedHeuristicAgent1("WeightedHeuristic 1"))
    players.append(simple_agents.WeightedHeuristicAgent2("WeightedHeuristic 2"))
    players.append(mdp_agent.MDPAgent("MDP-Inspired"))
    
    
    simulate_many_games(1, players)