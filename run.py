from dataclasses import replace
from random import choice
from typing import Type
import uno

def simulate_game(debug: bool = False, 
                  player1: uno.Player = uno.Player("Player 1"), 
                  player2: uno.Player = uno.Player("Player 2"), 
                  player3: uno.Player = uno.Player("Player 3"), 
                  player4: uno.Player = uno.Player("Player 4")) -> tuple[str, int]:
    players = [player1, player2, player3, player4]

    deck = uno.Deck()
    deck.shuffle()

    turn: int = 0
    turn_counter: int = 0
    direction: int = 1

    for _ in range(0, 7):
        for player in players:
            player.draw_card(deck.draw())
            
    def next_player(turn: int) -> int:
        turn += direction
        if turn > players.__len__() - 1:
            turn = 0
            
        if turn < 0:
            turn = players.__len__() - 1
            
        return turn

    while True:
        if turn_counter > 10000:
            return ("Timed Out", turn_counter)
        
        current_player = players[turn]
        card_played = False

        for card in current_player.hand:
            if deck.can_play_card(card):
                current_player.play_card(card, deck)
                card_played = True
                
                if debug:
                    print(f"{current_player.name} plays {str(card)}.")
                
                if card.value == uno.Value.REVERSE:
                    direction *= -1
                    
                if card.value == uno.Value.SKIP:
                    turn = next_player(turn)
                    
                if card.value == uno.Value.DRAW_TWO:
                    next = next_player(turn)
                    for i in range(0, 2):
                        players[next].draw_card(deck.draw())
                    turn = next_player(next)
                    
                if card.value in [uno.Value.WILD, uno.Value.DRAW_FOUR]:
                    new_color = choice([uno.Color.RED, uno.Color.YELLOW, uno.Color.GREEN, uno.Color.BLUE])
                    deck.discard[0] = replace(deck.discard[0], color=new_color)
                    
                    if debug:
                        print(f"{current_player.name} changes color to {new_color.value}.")
                
                if card.value == uno.Value.DRAW_FOUR:
                    next = next_player(turn)
                    for i in range(0, 4):
                        players[next].draw_card(deck.draw())
                    turn = next_player(next)
                    
                break
            
        if current_player.hand.__len__() == 0:
            if debug:
                print(f"{current_player.name} wins!")
                print(f"Game ended in {turn_counter} turns.")
                
            return (current_player.name, turn_counter)
            
        if not card_played:
            if debug:
                print(f"{current_player.name} draws.")
                
            current_player.draw_card(deck.draw())
            
        current_player.shuffle_hand()
        turn = next_player(turn)
        turn_counter += 1
        
# simulate_many_games() : Runs "n" games of UNO using simulate_game()
def simulate_many_games(n: int, debug: bool = False) -> None:
    game_results: list[tuple[str, int]] = []
    for _ in range(0, n):
        game_results.append(simulate_game(debug))
        
    print("Player Wins:\n")

    player_wins = {}
    for result in game_results:
        player_wins[result[0]] = player_wins.get(result[0], 0) + 1
        
    for player, wins in player_wins.items():
        print(f"{player}: {wins}")

if __name__ == "__main__":
    simulate_many_games(1000)