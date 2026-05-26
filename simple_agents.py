from uno import *

class Firsty(Player):
    # The agent plays the first playable card in its hand.
    pass # The normal Player class already does this. We're giving it a more explicit name.

class Randy(Player):
    # The agent plays a random playable card in its hand.
    # Almost the same as default, just calls shuffle_hand() before playing a card.
    def play_card(self, g_state: GameState) -> Card | bool:
        self.shuffle_hand()
        for card in self.hand:
            playable = g_state.deck.can_play_card(card)
            if playable:
                self.hand.remove(card)
                return card
        return False
    
class Powery(Player):
    # The agent will play power cards first.
    def play_card(self, g_state: GameState) -> Card | bool:
        self.shuffle_hand()
        # Check for power cards:
        for card in self.hand:
            playable = g_state.deck.can_play_card(card) and (card in [Value.SKIP, Value.REVERSE, Value.DRAW_TWO, Value.DRAW_FOUR, Value.WILD])
            if playable:
                self.hand.remove(card)
                return card
        
        # If no playable power cards are found, check the whole hand:
        for card in self.hand:
            playable = g_state.deck.can_play_card(card)
            if playable:
                self.hand.remove(card)
                return card
        return False
    

class Waity(Player):
    # The agent will play power cards last.
    def play_card(self, g_state: GameState) -> Card | bool:
        self.shuffle_hand()
        # Check for non-power cards:
        for card in self.hand:
            playable = g_state.deck.can_play_card(card) and (card not in [Value.SKIP, Value.REVERSE, Value.DRAW_TWO, Value.DRAW_FOUR, Value.WILD])
            if playable:
                self.hand.remove(card)
                return card
        
        # If no playable non-power cards are found, check the whole hand:
        for card in self.hand:
            playable = g_state.deck.can_play_card(card)
            if playable:
                self.hand.remove(card)
                return card
        return False