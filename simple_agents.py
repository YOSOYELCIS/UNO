from uno import *

POWER_VALS = [Value.SKIP, Value.REVERSE, Value.DRAW_TWO, Value.DRAW_FOUR, Value.WILD]
ATTACK_VALS = [Value.SKIP, Value.REVERSE, Value.DRAW_TWO, Value.DRAW_FOUR]
NUM_VALS = {
    Value.ZERO: 0,
    Value.ONE: 1,
    Value.TWO: 2,
    Value.THREE: 3,
    Value.FOUR: 4,
    Value.FIVE: 5,
    Value.SIX: 6,
    Value.SEVEN: 7,
    Value.EIGHT: 8,
    Value.NINE: 9,
}


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
            playable = g_state.deck.can_play_card(card) and (card.value in POWER_VALS)
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
            playable = g_state.deck.can_play_card(card) and (card.value not in POWER_VALS)
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
    
class SimpleTreeAgent(Player):
    """
    A heuristic-based UNO agent that uses a simple decision tree
    to select moves strategically instead of randomly.

    Agent Strategy Priority:
    1. Play a winning card if possible.
    2. If the next player is close to winning, prioritize
       disruptive action cards:
           - Skip
           - Reverse
           - Draw Two
           - Draw Four
    3. Prefer stronger utility cards over weaker ones.
    4. Use Wild cards to switch to the color most common
       in the agent's remaining hand.
    5. Otherwise, play the highest-scoring legal card.
    """

    def play_card(self, g_state: GameState) -> Card | bool:
        playable_cards = [card for card in self.hand if g_state.deck.can_play_card(card)]

        if not playable_cards:
            return False
        
        # Decision 1: Last card to play (UNO)
        # Decision 1: Last card to play (UNO)
        if len(self.hand) == 1:
            chosen = playable_cards[0]
            self.hand.remove(chosen)
            return chosen
        
        # Decision 2: Play an attack/action card?
        attack_cards = [card for card in playable_cards if card.value in ATTACK_VALS]
        if attack_cards:
            chosen = self.best_card(attack_cards)
            self.hand.remove(chosen)
            return chosen
        
        # Decision 3: Play a Wild?
        wild_cards = [card for card in playable_cards if card.value == Value.WILD]
        if wild_cards:
            chosen = self.best_card(wild_cards)
            self.hand.remove(chosen)
            return chosen
        
        # Decision 4: Play highest-value playable card.
        chosen = self.best_card(playable_cards)
        self.hand.remove(chosen)
        return chosen
    
    def best_card(self, cards: list[Card]) -> Card:
        return max(cards, key=self.card_score)

    def card_score(self, card: Card) -> int:
        """
        Assigns a heuristic utility score to a card.
        Higher scores represent stronger strategic value.

        Utility Ranking:
        Draw Four > Wild > Action Cards > Number Cards
        """
        if card.value == Value.DRAW_FOUR:
            return 20
        if card.value == Value.WILD:
            return 15
        if card.value in [Value.SKIP, Value.REVERSE, Value.DRAW_TWO]:
            return 10
        return NUM_VALS.get(card.value, 0)

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
            score += NUM_VALS.get(card.value, 0)

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
            score += NUM_VALS.get(card.value, 0)

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

        # 7. Slightly prefer higher number cards
        score += NUM_VALS.get(card.value, 0)

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