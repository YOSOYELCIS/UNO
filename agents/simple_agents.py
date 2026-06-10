from uno import *

# POWER cards are just the Black cards.
POWER = [
    Value.SKIP, 
    Value.REVERSE, 
    Value.DRAW_TWO, 
    Value.DRAW_FOUR, 
    Value.WILD
]

# ATTACK cards purposefully screw other players
# over by causing their turn to end or to 
# be unable to play after the current state.
ATTACK = [
    Value.SKIP, 
    Value.REVERSE, 
    Value.DRAW_TWO, 
    Value.DRAW_FOUR
]

# NUM cards are number cards.
NUM = [
    Value.ZERO,
    Value.ONE,
    Value.TWO,
    Value.THREE,
    Value.FOUR,
    Value.FIVE,
    Value.SIX,
    Value.SEVEN,
    Value.EIGHT,
    Value.NINE
] 
    
# Default player behavior.
class Default(Player):
    pass
    
# Shuffles the player's hand prior to playing a card.
# (could matter. could not. still fun)
class Shuffle(Player):
    def play_card(self, g_state: GameState) -> Card | bool:
        self.shuffle_hand()
        
        for card in self.hand:
            playable = g_state.deck.can_play_card(card)
            if playable:
                self.hand.remove(card)
                return card
            
        return False
    
# Attempts to play the first POWER card in their hand
# when presented with the option, otherwise tries to play
# a matching number card.
class Power(Player):
    def play_card(self, g_state: GameState) -> Card | bool:
        self.shuffle_hand()
        
        # Checks for power cards.
        for card in self.hand:
            playable = g_state.deck.can_play_card(card) and (card.value in POWER)
            if playable:
                self.hand.remove(card)
                return card
        
        # Checks the rest of the hand.
        for card in self.hand:
            playable = g_state.deck.can_play_card(card)
            if playable:
                self.hand.remove(card)
                return card
            
        return False
    

# Attempts to avoid playing POWER cards unless it is absolutely
# necessary to do so, opting to match color or number.
class Wait(Player):
    # The agent will play power cards last.
    def play_card(self, g_state: GameState) -> Card | bool:
        self.shuffle_hand()
        
        # Check for non-power cards.
        for card in self.hand:
            playable = g_state.deck.can_play_card(card) and (card.value not in POWER)
            if playable:
                self.hand.remove(card)
                return card
        
        # Checks the rest of the hand.
        for card in self.hand:
            playable = g_state.deck.can_play_card(card)
            if playable:
                self.hand.remove(card)
                return card

        return False
    
"""

A heuristic-based UNO agent that uses a simple decision tree
to select moves strategically instead of randomly.

* Play a winning card if possible.
* Prioritize ATTACK cards with the highest utility.

* Switch the color to the most common card in the agent's hand.
* Otherwise, play a legal card.

"""
class SimpleTreeAgent(Player):
    def play_card(self, g_state: GameState) -> Card | bool:
        # If no card is playable, then the player is forced to draw.
        playable_cards = [card for card in self.hand if g_state.deck.can_play_card(card)]
        if not playable_cards:
            return False
        
        # If the agent can play their last card, then they 
        # should prioritize winning.
        if len(self.hand) == 1:
            chosen = playable_cards[0]
            self.hand.remove(chosen)
            return chosen
        
        # Play the ATTACK card with the highest utility.
        attack_cards = [card for card in playable_cards if card.value in ATTACK]
        if attack_cards:
            chosen = self.best_card(attack_cards)
            self.hand.remove(chosen)
            return chosen
        
        # Play a Wild card and switch to an optimal color.
        wild_cards = [card for card in playable_cards if card.value == Value.WILD]
        if wild_cards:
            chosen = self.best_card(wild_cards)
            self.hand.remove(chosen)
            return chosen
        
        # Play a random playable card (should just be numbers).
        chosen = self.best_card(playable_cards)
        self.hand.remove(chosen)
        return chosen
    
    # Returns the card with the highest card utility.
    def best_card(self, cards: list[Card]) -> Card:
        return max(cards, key=self.card_score)

    def card_score(self, card: Card) -> int:
        match card.value:
            case Value.DRAW_FOUR:
                return 20
            
            case Value.DRAW_TWO:
                return 18
            
            case Value.SKIP:
                return 12
            
            case Value.REVERSE:
                return 10

        # All number cards TECHNICALLY have the same utility here...
        # I guess in a perfect world, you would have to find some world where
        # you can play a card that doesn't match for higher utility, but this
        # literally can only happen with a wild, so why does it matter?
        # Just a random thought I had whilst refactoring.
        
        return 1

    # Count how many cards of each color exist in the user's hand
    # (ignoring Black, of course) and then return that highest count.
    def choose_color(self):
        color_counts = {
            Color.RED: 0,
            Color.YELLOW: 0,
            Color.GREEN: 0,
            Color.BLUE: 0,
        }

        for card in self.hand:
            if card.color in color_counts:
                color_counts[card.color] += 1

        return max(color_counts, key=color_counts.get)