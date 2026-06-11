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

# A heuristic-based UNO agent that uses a simple decision tree
# to select moves strategically instead of fully randomly.
# 
# * Plays a winning card if possible.
# * Prioritizes ATTACK cards with the highest utility.
# * Switches the color to the most common card in the agent's hand.
# * Otherwise, plays a legal card.
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
    
# Weight heuristic agents.
class WeightedHeuristicAgent1(Player):
    """
    A more advanced heuristic UNO agent.

    Instead of ranking cards only by type, this agent evaluates each
    playable card using multiple weighted features:

    1. Card power
    2. Color control
    3. Hand reduction
    4. Endgame pressure
    5. Wild card usefulness
    """

    def play_card(self, g_state: GameState) -> Card | bool:
        playable_cards = [
            card for card in self.hand
            if g_state.deck.can_play_card(card)
        ]

        if not playable_cards:
            return False

        chosen = self.best_card(playable_cards, g_state)
        self.hand.remove(chosen)
        return chosen

    def best_card(self, cards: list[Card], g_state: GameState) -> Card:
        return max(cards, key=lambda card: self.card_score(card, g_state))

    def card_score(self, card: Card, g_state: GameState) -> int:
        score = 0

        # Feature 1: Card power
        if card.value == Value.DRAW_FOUR:
            score += 25
        elif card.value == Value.WILD:
            score += 18
        elif card.value == Value.DRAW_TWO:
            score += 15
        elif card.value in [Value.SKIP, Value.REVERSE]:
            score += 12
        else:
            score += 1

        # Feature 2: Prefer colors we have more of
        if card.color != Color.BLACK:
            same_color_count = sum(
                1 for c in self.hand
                if c.color == card.color
            )
            score += same_color_count * 3

        # Feature 3: Prefer getting rid of rare colors
        if card.color != Color.BLACK:
            same_color_count = sum(
                1 for c in self.hand
                if c.color == card.color
            )

            if same_color_count == 1:
                score += 4

        # Feature 4: Big bonus for winning move
        if len(self.hand) == 1:
            score += 100

        # Feature 5: Avoid wasting Wild too early
        if card.color == Color.BLACK and len(self.hand) > 4:
            score -= 5

        return score

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
    
class WeightedHeuristicAgent2(Player):
    """
    Advanced heuristic UNO agent.

    This agent scores each legal move using multiple strategic features:
    - winning immediately
    - reducing hand size
    - preserving future playable colors
    - avoiding wasting Wild/Draw Four too early
    - using attack cards more aggressively near the endgame
    """

    def play_card(self, g_state: GameState) -> Card | bool:
        playable_cards = [
            card for card in self.hand
            if g_state.deck.can_play_card(card)
        ]

        if not playable_cards:
            return False

        chosen = self.best_card(playable_cards, g_state)
        self.hand.remove(chosen)
        return chosen

    def best_card(self, cards: list[Card], g_state: GameState) -> Card:
        return max(cards, key=lambda card: self.card_score(card, g_state))

    def card_score(self, card: Card, g_state: GameState) -> int:
        score = 0

        hand_size = len(self.hand)

        # 1. Winning move should always be highest priority
        if hand_size == 1:
            return 1000

        # 2. Base card value
        if card.value == Value.DRAW_FOUR:
            score += 35
        elif card.value == Value.WILD:
            score += 25
        elif card.value == Value.DRAW_TWO:
            score += 22
        elif card.value == Value.SKIP:
            score += 18
        elif card.value == Value.REVERSE:
            score += 14
        else:
            score += 1

        # 3. Endgame: action cards become more valuable
        if hand_size <= 3:
            if card.value == Value.DRAW_FOUR:
                score += 40
            elif card.value == Value.DRAW_TWO:
                score += 30
            elif card.value in [Value.SKIP, Value.REVERSE]:
                score += 20
            elif card.value == Value.WILD:
                score += 15

        # 4. Early game: avoid wasting Wild/Draw Four too soon
        if hand_size >= 6:
            if card.value == Value.DRAW_FOUR:
                score -= 25
            elif card.value == Value.WILD:
                score -= 18

        # 5. Prefer playing colors we have fewer of to reduce color diversity
        if card.color != Color.BLACK:
            same_color_count = sum(
                1 for c in self.hand
                if c.color == card.color
            )

            # If this is the last card of that color, dump it
            if same_color_count == 1:
                score += 12
            else:
                score += same_color_count * 2

        # 6. Prefer matching by value over matching by color sometimes
        # This helps get rid of duplicate numbers/actions across colors.
        top_card = g_state.deck.discard[0]
        if card.value == top_card.value:
            score += 5

        score += 1
        return score

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


"""
Sample Test: 1000000 games

WeightedHeuristicAgent2: 170294
Firsty: 166179
Waity: 163928
WeightedHeurisitcAgent1: 146225
Randy: 137454
SimpleTreeAgent: 108255
Powery: 107665
"""

"""
MDPAgent: 172377
Firsty: 141409
Waity: 137008
WeightedHeurisitcAgent1: 125346
WeightedHeuristicAgent2: 123514
Randy: 115976
SimpleTreeAgent: 92691
Powery: 91679
"""