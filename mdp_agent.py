from uno import *

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

ACTION_VALS = [Value.SKIP, Value.REVERSE, Value.DRAW_TWO, Value.DRAW_FOUR]
REAL_COLORS = [Color.RED, Color.YELLOW, Color.GREEN, Color.BLUE]


class MDPAgent(Player):
    """
    MDP-style UNO agent.

    Chooses the card with the highest estimated Q-value:

        Q(s, a) = R(s, a) + gamma * V(s')
    """

    def __init__(self, name: str, gamma: float = 0.85):
        super().__init__(name)
        self.gamma = gamma

    def play_card(self, g_state: GameState) -> Card | bool:
        playable_cards = [
            card for card in self.hand
            if g_state.deck.can_play_card(card)
        ]

        if not playable_cards:
            return False

        chosen = self.best_action(playable_cards, g_state)
        self.hand.remove(chosen)
        return chosen

    def best_action(self, actions: list[Card], g_state: GameState) -> Card:
        return max(actions, key=lambda card: self.q_value(card, g_state))

    def q_value(self, card: Card, g_state: GameState) -> float:
        immediate_reward = self.reward(card, g_state)
        future_value = self.evaluate_successor_state(card, g_state)
        return immediate_reward + self.gamma * future_value

    def reward(self, card: Card, g_state: GameState) -> float:
        score = 0.0
        hand_size = len(self.hand)
        next_player = self.get_next_player(g_state, card)
        next_hand_size = len(next_player.hand) if next_player else 7

        if hand_size == 1:
            return 10000.0

        score += 40.0

        if card.value == Value.DRAW_FOUR:
            score += 90.0
        elif card.value == Value.DRAW_TWO:
            score += 65.0
        elif card.value == Value.SKIP:
            score += 45.0
        elif card.value == Value.REVERSE:
            score += 35.0
        elif card.value == Value.WILD:
            score += 50.0
        else:
            score += NUM_VALS.get(card.value, 0) * 2.0

        if next_hand_size <= 2:
            if card.value == Value.DRAW_FOUR:
                score += 180.0
            elif card.value == Value.DRAW_TWO:
                score += 140.0
            elif card.value in [Value.SKIP, Value.REVERSE]:
                score += 100.0
            elif card.value == Value.WILD:
                score += 45.0

        if hand_size <= 3:
            if card.value in [Value.DRAW_FOUR, Value.DRAW_TWO, Value.SKIP, Value.REVERSE]:
                score += 80.0
            elif card.value == Value.WILD:
                score += 50.0

        if hand_size >= 6:
            if card.value == Value.DRAW_FOUR and next_hand_size > 3:
                score -= 60.0
            elif card.value == Value.WILD:
                score -= 40.0

        return score

    def evaluate_successor_state(self, card: Card, g_state: GameState) -> float:
        value = 0.0
        remaining_hand = self.remaining_hand_after(card)
        next_player = self.get_next_player(g_state, card)

        opponent_hand_sizes = [
            len(player.hand)
            for player in g_state.players
            if player is not self
        ]

        value -= len(remaining_hand) * 25.0

        if len(remaining_hand) == 1:
            value += 250.0

        resulting_color = self.resulting_color_after(card, remaining_hand)

        same_color_remaining = sum(
            1 for c in remaining_hand
            if c.color == resulting_color or c.color == Color.BLACK
        )
        value += same_color_remaining * 30.0

        future_options = self.count_future_playable_cards(
            remaining_hand,
            card,
            resulting_color
        )
        value += future_options * 20.0

        if card.color != Color.BLACK:
            color_count_before = sum(
                1 for c in self.hand
                if c.color == card.color
            )
            if color_count_before == 1:
                value += 35.0

        top_card = g_state.deck.discard[0]
        if card.value == top_card.value:
            value += 20.0

        if opponent_hand_sizes:
            smallest_opponent_hand = min(opponent_hand_sizes)
            value -= max(0, 4 - smallest_opponent_hand) * 35.0

        if next_player:
            if card.value == Value.DRAW_TWO:
                value += 70.0
            elif card.value == Value.DRAW_FOUR:
                value += 120.0
            elif card.value == Value.SKIP:
                value += 60.0

        return value

    def remaining_hand_after(self, card: Card) -> list[Card]:
        remaining = self.hand.copy()
        if card in remaining:
            remaining.remove(card)
        return remaining

    def resulting_color_after(
        self,
        card: Card,
        remaining_hand: list[Card]
    ) -> Color:
        if card.color != Color.BLACK:
            return card.color
        return self.best_color_for_hand(remaining_hand)

    def count_future_playable_cards(
        self,
        remaining_hand: list[Card],
        played_card: Card,
        resulting_color: Color
    ) -> int:
        count = 0

        for candidate in remaining_hand:
            if (
                candidate.color == resulting_color
                or candidate.value == played_card.value
                or candidate.color == Color.BLACK
            ):
                count += 1

        return count

    def get_next_player(self, g_state: GameState, card: Card) -> Player | None:
        if g_state.player_count <= 1:
            return None

        direction = g_state.direction

        if card.value == Value.REVERSE:
            direction *= -1

        next_index = (g_state.turn + direction) % g_state.player_count
        return g_state.players[next_index]

    def choose_color(self) -> Color:
        return self.best_color_for_hand(self.hand)

    def best_color_for_hand(self, hand: list[Card]) -> Color:
        color_scores = {color: 0.0 for color in REAL_COLORS}

        for card in hand:
            if card.color in color_scores:
                color_scores[card.color] += 1.0

                if card.value in ACTION_VALS:
                    color_scores[card.color] += 1.5
                else:
                    color_scores[card.color] += NUM_VALS.get(card.value, 0) / 10.0

        return max(color_scores, key=color_scores.get)