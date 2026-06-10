import copy
from uno import *
from collections import Counter
from random import random

class CardDistribution():
    """
    Stores the non-normalized distribution so that we can add or subtract from the count certain cards in the distribution.
    """
    unnormalized_dist: dict[Card, float]
    
    def __init__(self, possible_cards: list[Card]):
        """
        Produces a distribution of cards to probabilities based on a list of possible card values where the same card value may appear more than once
        """
        self.unnormalized_dist = dict(Counter(possible_cards))
    
    def normalize(self) -> dict[Card, float]:
        """
        Returns the normalized distribution of self.unnormalized
        """
        filtered = {card: count for card, count in self.unnormalized_dist.items() if count > 0}
        total = sum(filtered.values())
        if total == 0:
            raise ValueError("Cannot normalize empty distribution")
        return {card: value / total for card, value in filtered.items()}
    
    def sample_destructive(self) -> Card:
        r = random()
        cumulative = 0.0

        sample = next(iter(self.normalize())) # Just in case we don't get a sample from the below
        for card, prob in self.normalize().items():
            cumulative += prob
            if r < cumulative:
                sample = card
                break
        
        self.unnormalized_dist[sample] -= 1
        if self.unnormalized_dist[sample] < 0:
            raise ValueError(f"Tried to sample card {sample} with count {self.unnormalized_dist[sample]}")
        return sample
    
    def is_empty(self) -> bool:
        return not any(self.unnormalized_dist.values())

class GameStateDistribution():
    """
    Stores the non-normalized distribution so that we can add or subtract from the count certain cards in the distribution.
    """
    unnormalized_dist: dict[GameState, float]
    normalized_dist: dict[GameState, float]
    
    def __init__(self, possible_states: list[GameState]):
        """
        Produces a distribution of cards to probabilities based on a list of possible card values where the same card value may appear more than once
        """
        self.unnormalized_dist = dict(Counter(possible_states))
        self.normalized_dist = self.normalize(self.unnormalized_dist)
    
    def normalize[A](self, distr: dict[A, float]) -> dict[A, float]:
        """
        Normalizes a distribution
        """
        total = sum(value for value in distr.values())
        normalized_dist = {key: value/total for key, value in distr.items()}
        return normalized_dist
    
    def sample(self) -> GameState:
        r = random()
        cumulative = 0.0

        for state, prob in self.normalized_dist.items():
            cumulative += prob
            if r < cumulative:
                return state
        
        return state # If we never get a state, return the last state processed


class MDP_Agent(Player):
    """
    The MDP Agent maintains and updates a distribution every turn based on the discard pile and its own hand expressing the probabilities of cards in other players' hands. It then uses that distribution to predict future turns, choosing the action (which card to play) with the highest expected utility.
    """
    name: str
    hand: list[Card]
    sample_count: int  # Number of samples to use when generating a distribution
    prediction_depth: int # Number of turns into the future that the agent predicts when considering playing a card. (A turn meaning when the agent gets to act again, not the literal next opponent's turn)
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
                 name: str, sample_count: int = 5, 
                 prediction_depth: int = 3, 
                 discount_factor: float = 0.75, 
                 survival_reward: int = 20, 
                 draw_penalty: int = -10, 
                 win_reward: int = 100, 
                 loss_penalty: int = -100, 
                 hand_size_penalty: int = 1, 
                 lowest_opponent_hand_size_reward: int = 2):
        """Modified init allows instantiating the class with special reward/penalty values to support fine tuning"""
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

    def play_card(self, g_state: GameState) -> Card | bool:
        self.own_index: int = g_state.turn
        
        card, value = self.get_best_action(g_state, self.prediction_depth)

        return card

    def get_best_action(self, g_state: GameState, depth: int) -> tuple[Card | bool, float]:
        """
        Returns the best action by assembling and sampling game-state distributions.
        Calculates the expected value of playing a card by making a distribution of the next turn with sampling, then using that distribution to the next.
        """
        playable_cards = [card for card in self.hand if g_state.deck.can_play_card(card)]

        if not(playable_cards):
            # If we can't play any cards, draw
            return False, self.draw_penalty  
        elif len(playable_cards) == 1:
            # If we can only play one card, play that card
            return playable_cards[0], self.reward(g_state.simulate_turn(playable_cards[0])) 
        
        expected_values: dict[Card, float] = {card: 0 for card in playable_cards}
        for card in playable_cards:
            instant_result: GameState = g_state.simulate_turn(card)
            next_state_dist = self.sample_next_turn(GameStateDistribution([instant_result]))
            
            future_value = 0
            for next_state in next_state_dist.normalized_dist:
                prob = next_state_dist.normalized_dist[next_state]
                future_value += prob * self.value(next_state, depth-1)

            expected_values[card] = self.reward(instant_result) + self.discount_factor * future_value
        return max(expected_values.items(), key=lambda item: item[1])

    def value(self, state: GameState, depth: int):
        if depth == 0:
            return self.reward(state)
        elif state.game_end:
            return self.reward(state)
        else:
            simplified_state = self.simplify_state(state)
            if simplified_state in self.state_values:
                # If we've already calculated a value for the simplified state, we can return its pre-computed value
                return self.state_values[simplified_state]
            
            _, future_value = self.get_best_action(state, depth - 1)
            total_reward = self.reward(state) + self.discount_factor * future_value
            self.state_values[simplified_state] = total_reward
            return total_reward
    
    def simplify_state(self, state: GameState):
        """
        Simplifying the game state allows us to pretend different states have the same value, meaning when we encounter them we can just default to the value we previously computed instead of diving into get_best_action all over again.
        """
        players = state.players
        hand_length_of_self: int = players[self.own_index].hand.__len__()
        smallest_hand_length_among_opponents: int = min([player.hand.__len__() for i, player in enumerate(state.players) if i != self.own_index])
        has_playable_card: bool = any(state.deck.can_play_card(card) for card in players[self.own_index].hand)
        return (hand_length_of_self, smallest_hand_length_among_opponents, has_playable_card)

    def sample_next_turn(self, game_state_dist: GameStateDistribution) -> GameStateDistribution:
        """
        Uses samples of the given game state distribution to assemble a new game state distribution for the next time it is the current agent's turn
        """
        samples = []
        for _ in range(self.sample_count):
            # Take samples a number of times equal to self.sample_count
            s_game_state = game_state_dist.sample()
            s_oppenent_card_dist = self.opponent_dist_from_state(s_game_state, self.own_index)
            for player_index in range(s_game_state.player_count):
                # After we take a sample, we populate the hands of the opponents by some very small sampling (this is O(1) since player hands are always relatively small)
                if (player_index == self.own_index):
                    continue
                opponent = s_game_state.players[player_index]
                opponent_hand_length = opponent.hand.__len__()
                opponent.hand = []
                for _ in range(opponent_hand_length):
                    opponent.hand.append(s_oppenent_card_dist.sample_destructive())
            # Now that we sampled player hands, the remaining cards are in the draw pile:
            s_game_state.deck.pile = []
            while not s_oppenent_card_dist.is_empty():
                s_game_state.deck.pile.append(s_oppenent_card_dist.sample_destructive())
            
            # Now the sample game state reflects our agent's uncertainty, we can simulate opponents playing cards until it's our agent's turn again.
            while not (s_game_state.turn == self.own_index or s_game_state.game_end):
                s_game_state.process_turn()
            # Now it's our agent's turn again! Add the current state to the list to be made into a distribution
            samples.append(copy.copy(s_game_state))
        
        # Now we have a bunch of samples and can make a distribution for what the game state will be the next time it's our agent's turn
        return GameStateDistribution(samples)

    
    @staticmethod
    def opponent_dist_from_state(game_state: GameState, agent_index: int) -> CardDistribution:
        return CardDistribution([card for card in game_state.deck.full_deck if card not in game_state.players[agent_index].hand + game_state.deck.discard])
    
    def reward(self, gamestate: GameState) -> float:
        """
        Calculates a reward for the current state based on hand length, whether the agent or an opponent has won, the size of the smallest opponent hand, etc.
        Currently only uses hand_length
        """
        hand_length = gamestate.players[self.own_index].hand.__len__()
        if (hand_length == 0):
            return self.win_reward
        else:
            return self.survival_reward - hand_length*self.hand_size_penalty