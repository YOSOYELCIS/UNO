import copy
from dataclasses import replace
from uno import *


class ExpectimaxAgent(Player):
    """
    A small expectimax template for UNO.

    The idea:
    - On our turns, choose the move with the highest expected value.
    - On opponent turns, treat each legal opponent move as equally likely.
    - Stop after a small depth and score the resulting state.

    Keep `depth` between 1 and 3 while experimenting. Bigger depths get slow
    quickly because each card choice creates another branch in the tree.
    """

    def __init__(
        self,
        name: str,
        depth: int = 2,
        hand_size_weight: float = 4.0,
        playable_card_weight: float = 1.5,
        win_score: float = 1000.0,
        loss_score: float = -1000.0,
    ):
        super().__init__(name)
        self.depth = max(1, min(depth, 3))
        self.hand_size_weight = hand_size_weight
        self.playable_card_weight = playable_card_weight
        self.win_score = win_score
        self.loss_score = loss_score
        self.own_index = 0

    def play_card(self, g_state: GameState) -> Card | bool:
        """
        Called by GameState.process_turn().

        IMPORTANT: Player.play_card implementations remove the chosen card from
        their hand before returning it, so this method does that too.
        """
        self.own_index = g_state.turn
        playable_cards = self.legal_actions(g_state, self.own_index)

        if not playable_cards:
            return False

        chosen_card = self.best_action(g_state, playable_cards)
        self.hand.remove(chosen_card)
        return chosen_card

    def best_action(self, g_state: GameState, playable_cards: list[Card]) -> Card:
        """
        Try each legal card, simulate it, and keep the highest-value result.

        This is the "max": when it is our turn, we assume we
        will choose the action that looks best.
        """

        best_card = playable_cards[0]
        best_value = float("-inf")

        for card in playable_cards:
            next_state = self.simulate_action(g_state, card)
            value = self.expectimax(next_state, self.depth - 1)

            if value > best_value:
                best_card = card
                best_value = value

        return best_card

    def expectimax(self, g_state: GameState, depth: int) -> float:
        """
        Recursively estimate the value of a state.

        If it is our turn, we maximize.
        If it is an opponent's turn, we average over their legal actions.
        """
        if depth == 0 or g_state.game_end:
            return self.evaluate(g_state)

        current_index = g_state.turn
        actions = self.legal_actions(g_state, current_index)

        # If a player has no legal card, the only action is drawing.
        if not actions:
            actions = [False]

        if current_index == self.own_index:
            return max(
                self.expectimax(self.simulate_action(g_state, action), depth - 1)
                for action in actions
            )

        # Chance node: this template assumes opponents choose uniformly from
        # their legal moves. This is the probabilistic part you can refine later.
        action_probability = 1 / len(actions)
        return sum(
            action_probability
            * self.expectimax(self.simulate_action(g_state, action), depth - 1)
            for action in actions
        )

    def evaluate(self, g_state: GameState) -> float:
        """
        Small scoring function for leaf states.

        Negative heuristic:
        - Fewer cards in our hand is better.

        Positive heuristic:
        - Having more playable cards is better because it gives us flexibility.

        Try changing these weights first. That is the easiest way to learn how
        this agent's choices are being shaped.
        """
        my_hand = g_state.players[self.own_index].hand

        if len(my_hand) == 0:
            return self.win_score

        for index, player in enumerate(g_state.players):
            if index != self.own_index and len(player.hand) == 0:
                return self.loss_score

        playable_count = len(self.legal_actions(g_state, self.own_index))
        return (
            -self.hand_size_weight * len(my_hand)
            + self.playable_card_weight * playable_count
        )

    @staticmethod
    def legal_actions(g_state: GameState, player_index: int) -> list[Card]:
        """Return every card that the given player can legally play right now."""
        player = g_state.players[player_index]
        return [card for card in player.hand if g_state.deck.can_play_card(card)]

    def simulate_action(self, g_state: GameState, action: Card | bool) -> GameState:
        """
        Simulate one turn without changing the real game.

        This mirrors GameState.process_turn(), but is kept here so the template
        is easy to inspect and modify while you are building the agent.
        """
        next_state = copy.deepcopy(g_state)
        current_player = next_state.players[next_state.turn]

        if type(action) == Card:
            current_player.hand.remove(action)
            next_state.deck.play_to_pile(action)

            match action.value:
                case Value.REVERSE:
                    next_state.direction *= -1

                case Value.SKIP:
                    next_state.next_player()

                case Value.DRAW_TWO:
                    skipped_player = next_state.next_player()
                    for _ in range(2):
                        next_state.players[skipped_player].draw_card(next_state.deck.draw())
                    next_state.next_player()

                case Value.WILD | Value.DRAW_FOUR:
                    new_color = current_player.choose_color()
                    next_state.deck.discard[0] = replace(
                        next_state.deck.discard[0],
                        color=new_color,
                    )

                    if action.value == Value.DRAW_FOUR:
                        skipped_player = next_state.next_player()
                        for _ in range(4):
                            next_state.players[skipped_player].draw_card(next_state.deck.draw())
                        next_state.next_player()

            if len(current_player.hand) == 0:
                next_state.game_end = True

        else:
            current_player.draw_card(next_state.deck.draw())

        next_state.next_player()
        next_state.turn_counter += 1
        return next_state

    def choose_color(self) -> Color:
        """
        Pick the color we have the most of after playing a Wild card.

        This is not really part of expectimax; it is just a simple helper so
        Wild cards behave sensibly in the existing UNO engine.
        """
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
