from uno import *

import copy
import random
from collections import Counter
from random import random as rand_float

class CardDistribution():
    # Stores the non-normalized distribution so that we can
    # add or subtract from the count of certain cards in the distribution.
    unnormalized_dist: dict[Card, float]
    normalized_dist: dict[Card, float]
    
    def __init__(self, possible_cards: list[Card]):
        self.unnormalized_dist = dict(Counter(possible_cards))

    # Normalizes the interal unnormalized distribution. 
    # Filters out cards with zero entries.
    def normalize(self) -> dict[Card, float]:
        filtered = {card: count for card, count in self.unnormalized_dist.items() if count > 0}
        total = sum(filtered.values())

        if total == 0:
            raise ValueError("Cannot normalize empty distribution")

        return {card: value / total for card, value in filtered.items()}

    # Samples a card proportional to its count, then decrements that count.
    # In order to prevent multiple normalizations (bad for runtime),
    # I cache the current normalization prior to modification.
    def sample_destructive(self) -> Card:
        cumulative, rand = cumulative, rand_float()
        normalized = self.normalize()  # cache — avoids calling twice

        # Default to the last card just in case
        # the rand <= cumulative clause never hits.
        sample = next(reversed(normalized))
        for card, prob in normalized.items():
            cumulative += prob
            if rand <= cumulative:
                sample = card
                break

        self.unnormalized_dist[sample] -= 1
        if self.unnormalized_dist[sample] < 0:
            raise ValueError(
                f"Tried to sample card {sample} but its count went negative"
            )

        return sample

    # CHecks to see if the current distribution is empty.
    def is_empty(self) -> bool:
        return not any(self.unnormalized_dist.values())

class GameStateDistribution():
    unnormalized_dist: dict[GameState, float]
    normalized_dist: dict[GameState, float]

    def __init__(self, possible_states: list[GameState]):
        self.unnormalized_dist = dict(Counter(possible_states))
        self.normalized_dist = self.normalize(self.unnormalized_dist)

    @staticmethod
    # Normalizes the GameState distribution.
    def normalize(distr: dict) -> dict:
        total = sum(distr.values())
        if total == 0:
            raise ValueError("Cannot normalize empty GameStateDistribution")
        
        return {state: value / total for state, value in distr.items()}

    def sample(self) -> GameState:
        cumulative, rand = 0.0, rand_float()
        last = next(reversed(self.normalized_dist))

        for state, prob in self.normalized_dist.items():
            cumulative += prob
            if r <= cumulative:
                return state
            last = state

        return last


class MDPAgent(Player):
    """
    The MDP Agent maintains and updates a distribution every turn based on
    the discard pile and its own hand, expressing the probabilities of cards
    in other players' hands. It then uses that distribution to predict future
    turns, choosing the action (which card to play) with the highest expected
    utility.
    """
    name: str
    hand: list[Card]
    sample_count: int        # Number of samples when generating a distribution
    prediction_depth: int    # Turns ahead the agent looks (agent turns, not all turns)
    discount_factor: float
    survival_reward: int
    draw_penalty: int
    win_reward: int
    loss_penalty: int
    hand_size_penalty: int
    lowest_opponent_hand_size_reward: int
    own_index: int
    state_values: dict[tuple[int, int, bool], float]

    def __init__(self,
                 name: str,
                 sample_count: int = 5,
                 prediction_depth: int = 3,
                 discount_factor: float = 0.75,
                 survival_reward: int = 20,
                 draw_penalty: int = -10,
                 win_reward: int = 100,
                 loss_penalty: int = -100,
                 hand_size_penalty: int = 1,
                 lowest_opponent_hand_size_reward: int = 2):
        self.name = name
        self.hand: list[Card] = []
        self.sample_count = sample_count
        self.prediction_depth = prediction_depth
        self.discount_factor = discount_factor
        self.survival_reward = survival_reward
        self.draw_penalty = draw_penalty
        self.win_reward = win_reward
        self.loss_penalty = loss_penalty
        self.hand_size_penalty = hand_size_penalty
        self.lowest_opponent_hand_size_reward = lowest_opponent_hand_size_reward
        self.state_values = {}
        self.own_index = -1

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def play_card(self, g_state: GameState) -> Card | bool:
        # Capture our seat index; clear the value cache at the start of
        # each new game (own_index == -1) or whenever our index changes.
        new_index = g_state.turn
        if new_index != self.own_index:
            self.own_index = new_index
            self.state_values = {}

        card, _ = self.get_best_action(g_state, self.prediction_depth)
        return card

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------

    def get_best_action(self, g_state: GameState, depth: int) -> tuple[Card | bool, float]:
        """
        Returns (best_card_or_False, expected_value).
        Assembles a sampled next-state distribution for each playable card
        and picks the one with highest expected value.
        """
        playable_cards = [
            card for card in self.hand if g_state.deck.can_play_card(card)
        ]

        if not playable_cards:
            return False, self.draw_penalty

        if len(playable_cards) == 1:
            instant_result = g_state.simulate_turn(playable_cards[0])
            return playable_cards[0], self.reward(instant_result)

        expected_values: dict[Card, float] = {}
        for card in playable_cards:
            instant_result: GameState = g_state.simulate_turn(card)
            next_state_dist = self.sample_next_turn(
                GameStateDistribution([instant_result])
            )

            future_value = 0.0
            for next_state, prob in next_state_dist.normalized_dist.items():
                future_value += prob * self.value(next_state, depth - 1)

            expected_values[card] = (
                self.reward(instant_result) + self.discount_factor * future_value
            )

        return max(expected_values.items(), key=lambda item: item[1])

    def value(self, state: GameState, depth: int) -> float:
        if depth == 0 or state.game_end:
            return self.reward(state)

        simplified = self.simplify_state(state)
        if simplified in self.state_values:
            return self.state_values[simplified]

        _, future_value = self.get_best_action(state, depth - 1)
        total_reward = self.reward(state) + self.discount_factor * future_value
        self.state_values[simplified] = total_reward
        return total_reward

    def simplify_state(self, state: GameState) -> tuple[int, int, bool]:
        """
        Collapses a full GameState to a small key for value-function caching.
        """
        players = state.players
        hand_length_of_self: int = len(players[self.own_index].hand)
        smallest_opponent_hand: int = min(
            len(players[i].hand)
            for i in range(len(players))
            if i != self.own_index
        )
        has_playable_card: bool = any(
            state.deck.can_play_card(card)
            for card in players[self.own_index].hand
        )
        return (hand_length_of_self, smallest_opponent_hand, has_playable_card)

    # ------------------------------------------------------------------
    # Sampling
    # ------------------------------------------------------------------

    def sample_next_turn(self, game_state_dist: GameStateDistribution) -> GameStateDistribution:
        """
        Draws `self.sample_count` samples from game_state_dist, fills in
        opponent hands probabilistically, then simulates until it is our
        agent's turn again.  Returns a new GameStateDistribution over those
        resulting states.
        """
        samples: list[GameState] = []

        for _ in range(self.sample_count):
            # Deep-copy so we never mutate the shared source state.
            s_state = copy.deepcopy(game_state_dist.sample())
            s_card_dist = self.opponent_dist_from_state(s_state, self.own_index)

            # Deal sampled hands to every opponent.
            for player_index in range(s_state.player_count):
                if player_index == self.own_index:
                    continue
                opponent = s_state.players[player_index]
                hand_size = len(opponent.hand)
                opponent.hand = []
                for _ in range(hand_size):
                    if s_card_dist.is_empty():
                        break
                    opponent.hand.append(s_card_dist.sample_destructive())

            # Remaining un-dealt cards become the draw pile.
            s_state.deck.pile = []
            while not s_card_dist.is_empty():
                s_state.deck.pile.append(s_card_dist.sample_destructive())

            # Ensure there is always something to draw before simulating.
            self._ensure_drawable(s_state)

            # Simulate opponent turns until it's our turn (or the game ends).
            while not (s_state.turn == self.own_index or s_state.game_end):
                s_state.process_turn()
                self._ensure_drawable(s_state)

            # Deep-copy so each entry in `samples` is independent.
            samples.append(copy.deepcopy(s_state))

        if not samples:
            # Fallback: if every sample ended the game immediately, use the
            # original distribution so the caller always gets something valid.
            return game_state_dist

        return GameStateDistribution(samples)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_drawable(game_state: GameState) -> None:
        """
        If the draw pile is empty, reshuffle the discard pile (minus the top
        card) back into it — mirroring standard UNO rules.
        """
        if len(game_state.deck.pile) == 0 and len(game_state.deck.discard) > 1:
            top_card = game_state.deck.discard[-1]
            reshuffle = game_state.deck.discard[:-1]
            random.shuffle(reshuffle)
            game_state.deck.discard = [top_card]
            game_state.deck.pile = reshuffle

    @staticmethod
    def opponent_dist_from_state(game_state: GameState, agent_index: int) -> CardDistribution:
        """
        Builds a CardDistribution of every card NOT in the agent's hand and
        NOT in the discard pile — i.e. the cards that could be in opponents'
        hands or the draw pile.
        """
        known_cards = (
            game_state.players[agent_index].hand + game_state.deck.discard
        )
        unknown_cards = [
            card for card in game_state.deck.full_deck if card not in known_cards
        ]
        return CardDistribution(unknown_cards)

    def reward(self, gamestate: GameState) -> float:
        """
        Scalar reward for a game state.
        """
        hand_length = len(gamestate.players[self.own_index].hand)
        if hand_length == 0:
            return self.win_reward
        return self.survival_reward - hand_length * self.hand_size_penalty