import agents.mdp_agent as mdp_agent
import agents.simple_agents as simple_agents
import uno

# Simulates one game with default player behavior.
def simulate_game(
    players: list[uno.Player] = 
        [simple_agents.Default("Player 1"), 
         simple_agents.Default("Player 2"), 
         simple_agents.Default("Player 3"), 
         simple_agents.Default("Player 4")],
    debug: bool = False) -> tuple[str, int]:
    
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
        game_results.append(simulate_game(players, debug))
        
    print("Player Wins:\n")
    player_wins = {}
    for result in game_results:
        player_wins[result[0]] = player_wins.get(result[0], 0) + 1
        
    # Sorts in descending order of wins.
    win_counts = sorted(player_wins.items(), key=lambda element: element[1], reverse=True)
    for player, wins in win_counts:
        print(f"{player}: {wins}")

if __name__ == "__main__":
    players = [ 
        simple_agents.Default("Default 1"),
        simple_agents.Default("Default 2"),
        simple_agents.Default("Default 3"),
        mdp_agent.MDPAgent("MDP")]
    
    simulate_many_games(1, players)