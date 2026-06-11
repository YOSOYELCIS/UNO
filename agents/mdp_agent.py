import copy
from uno import *
from collections import Counter
from random import random, shuffle

# Default values for MDP agent sampling.
SAMPLE_COUNT = 5
PREDICTION_DEPTH = 3

DISCOUNT = 0.75
SURVIVAL_REWARD = 23
WIN_REWARD = 141
DRAW_PENALTY = -131
LOSS_PENALTY = -562

LOWEST_OPPONENT_HAND_SIZE_REWARD = 5
HAND_SIZE_PENALTY = -10
SIMULATED_TABLE_ROUNDS = 50

class CardDistribution():
    unnormalized_dist: dict[Card, float]
    
    def __init__(self, possible_cards: list[Card]):
        self.unnormalized_dist = dict(Counter(possible_cards))
    
    # Normalizes the set of cards by filtering out cards with
    # no pile distinction and then applying the average.
    def normalize(self) -> dict[Card, float]:
        
        filtered = {card: count for card, count in self.unnormalized_dist.items() if count > 0}
        total = sum(filtered.values())
        if total == 0:
            raise ValueError("Cannot normalize empty distribution")
        return {card: value / total for card, value in filtered.items()}
    
    # Samples from the normalized distribution, but removes
    # the card that is pulled, so the next iteration of sampling
    # does not treat the card as if it is still in the deck.
    def sample_destructive(self) -> Card:
        cumulative, rand = 0.0, random()

        # Sample from the current normalized card set
        # and decrement the counter of that card by 1.
        sample = next(iter(self.normalize()))
        for card, prob in self.normalize().items():
            cumulative += prob
            if rand <= cumulative:
                sample = card
                break
        
        self.unnormalized_dist[sample] -= 1
        if self.unnormalized_dist[sample] < 0:
            raise ValueError(f"Tried to sample card {sample} with count {self.unnormalized_dist[sample]}")
        
        return sample
    
    # Returns True if the card set is empty.
    def is_empty(self) -> bool:
        return not any(self.unnormalized_dist.values())

class GameStateDistribution():
    unnormalized_dist: dict[GameState, float]
    normalized_dist: dict[GameState, float]
    
    def __init__(self, possible_states: list[GameState]):
        self.unnormalized_dist = dict(Counter(possible_states))
        self.normalized_dist = self.normalize(self.unnormalized_dist)
    
    # Normalizes the GameState distribution.
    def normalize(self, distr: dict[GameState, float]) -> dict[GameState, float]:
        total = sum(value for value in distr.values())
        normalized_dist = {key: value/total for key, value in distr.items()}
        return normalized_dist
    
    # Samples from the GameState normalized distribution
    # or returns the last state found if nothing works.
    def sample(self) -> GameState:
        r = random()
        cumulative = 0.0

        for state, prob in self.normalized_dist.items():
            cumulative += prob
            if r < cumulative:
                return state
        
        return state
    
# The MDP Agent maintains and updates a distribution every turn based on 
# the discard pile and its own hand expressing the probabilities of cards in other players' hands. 
# It then uses that distribution to predict future turns, choosing the action 
# (which card to play) with the highest expected utility.
class MDPAgent(Player):
    
    name: str
    hand: list[Card]
    index: int
    
    # Sampling variables.
    sample_count: int 
    prediction_depth: int
    
    # Rewards + penaltys for weighing each possible outcome.
    discount_factor: float
    survival_reward: int
    draw_penalty: int
    win_reward: int
    loss_penalty: int
    hand_size_penalty: int
    lowest_opponent_hand_size_reward: int
    
    # Player data.
    state_values: dict[tuple[int, int, bool], float]
    
    def __init__(self, 
        name: str, 
        sample_count: int = SAMPLE_COUNT, 
        prediction_depth: int = PREDICTION_DEPTH, 
        discount_factor: float = DISCOUNT, 
        survival_reward: int = SURVIVAL_REWARD, 
        draw_penalty: int = DRAW_PENALTY, 
        win_reward: int = WIN_REWARD, 
        loss_penalty: int = LOSS_PENALTY, 
        hand_size_penalty: int = HAND_SIZE_PENALTY, 
        lowest_opponent_hand_size_reward: int = LOWEST_OPPONENT_HAND_SIZE_REWARD):
        
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

    # Plays the card corresponding to the action with the highest 
    # reward value, or False if the optimal (forced) move is to draw.
    def play_card(self, g_state: GameState) -> Card | bool:
        self.index: int = g_state.turn
        card, _ = self.get_best_action(g_state, self.prediction_depth)
        
        if card:
            self.hand.remove(card)
        return card
    
    # Recursively determines the best possible course of action by checking to see
    # if playing a certain playable card creates a state where utility is
    # maximized, returning after reaching a terminal state and calculating the
    # utility of the hand distribution across all players.
    def get_best_action(self, g_state: GameState, depth: int) -> tuple[Card | bool, float]:
        own_hand = g_state.players[self.index].hand
        playable_cards = [card for card in own_hand if g_state.deck.can_play_card(card)]

        # If no cards are playable, then ignore finding the best option,
        # because there is only one option. : (
        if not playable_cards:
            return False, self.draw_penalty

        expected_values: dict[Card, float] = {}

        for card in playable_cards:
            instant_result: GameState = g_state.simulate_turn(card)

            # If this is a terminal state, return instantaneous reward.
            if depth == 0 or instant_result.game_end:
                expected_values[card] = self.reward(instant_result)
            else:
                # Calculate the distribution of the next state and then 
                # find the expected value of playing a certain card.
                next_state_dist = self.sample_next_turn(GameStateDistribution([instant_result]))
                future_value = sum(
                    prob * self.value(next_state, depth - 1)
                    for next_state, prob in next_state_dist.normalized_dist.items()
                )
                expected_values[card] = self.reward(instant_result) + self.discount_factor * future_value

        # Return the best card to play and the value of ending up in that state.
        return max(expected_values.items(), key=lambda item: item[1])
    
    # Calculates the reward of the given GameState.
    def reward(self, state: GameState) -> float:
        hand_length = state.players[self.index].hand.__len__()
        
        if hand_length == 0:
            return self.win_reward
        else:
            return self.survival_reward - hand_length * self.hand_size_penalty

    # Calculates the value of the given GameState.
    def value(self, state: GameState, depth: int):
        if depth == 0 or state.game_end:
            return self.reward(state)
        else:
            # Reduces the current state to its most crucial elements
            # to prevent storing more in the state table.
            simplified_state = self.simplify_state(state)
            
            # Return memoized state if it already exists.
            if simplified_state in self.state_values:
                return self.state_values[simplified_state]
            
            _, future_value = self.get_best_action(state, depth - 1)
            total_reward = self.reward(state) + self.discount_factor * future_value
            self.state_values[simplified_state] = total_reward
            
            return total_reward
    
    # Memoization method for calculating simple GameStates, since reaching
    # the same state shouldn't need to be retallied
    def simplify_state(self, state: GameState):
        players = state.players
        hand_size = players[self.index].hand.__len__()
        smallest_opponent_hand = min([player.hand.__len__() for i, player in enumerate(state.players) if i != self.index])
        has_playable_card: bool = any(state.deck.can_play_card(card) for card in players[self.index].hand)
        
        return (
            hand_size, 
            smallest_opponent_hand, 
            has_playable_card
        )

    # Samples the next turn using the existing GameStateDistribution and calculates
    # the distribution of the following turns.
    def sample_next_turn(self, game_state_dist: GameStateDistribution) -> GameStateDistribution:
        samples = []
        
        for _ in range(self.sample_count):
            # Deepcopy to avoid mutating current state.
            s_game_state = copy.deepcopy(game_state_dist.sample())
            s_opponent_card_dist = self.opponent_dist_from_state(s_game_state, self.index)

            # Samples the hands of the other players by sampling 
            # from the opponent card distribution.
            for player_index in range(s_game_state.player_count):
                if player_index == self.index:
                    continue
                
                opponent = s_game_state.players[player_index]
                opponent_hand_length = len(opponent.hand)
                opponent.hand = []
                
                for _ in range(opponent_hand_length):
                    if s_opponent_card_dist.is_empty():
                        break
                    
                    opponent.hand.append(s_opponent_card_dist.sample_destructive())

            # Assign remaining undealt cards to draw pile.
            s_game_state.deck.pile = []
            while not s_opponent_card_dist.is_empty():
                s_game_state.deck.pile.append(s_opponent_card_dist.sample_destructive())

            # If draw pile is empty or very small, reshuffle discard (minus top card) back in.
            self.ensure_drawable(s_game_state)

            # This loop guarantees that a terminal state will be reached,
            # theoretically tracing the table SIMULATED_TABLE_ROUND times
            # before calling it (the game will go on, some way, somehow.)
            simulations = 0
            max_simulations = s_game_state.player_count * SIMULATED_TABLE_ROUNDS

            while not (s_game_state.turn == self.index or s_game_state.game_end):
                if simulations >= max_simulations:
                    break
                
                s_game_state.simulate_turn(s_game_state.players[s_game_state.turn].play_card(s_game_state))
                self.ensure_drawable(s_game_state)
                simulations += 1

            samples.append(copy.copy(s_game_state))

        return GameStateDistribution(samples)
    
    
    # Calculates the distribution of the cards in the hands of the
    # opponents by using all publically accessible information
    # (your hand and the discard pile determines what has to be in play / in the draw pile.)
    def opponent_dist_from_state(self, game_state: GameState, agent_index: int) -> CardDistribution:
        return CardDistribution([card for card in game_state.deck.full_deck if card not in game_state.players[agent_index].hand + game_state.deck.discard])

    # Ensures that the current GameState contains a card to draw from the top
    # of the pile to avoid a situation where the model attempts to simulate a 
    # draw, but is unable to do so after simulating a recursive action.
    def ensure_drawable(self, game_state: GameState) -> None:
        if len(game_state.deck.pile) == 0 and len(game_state.deck.discard) > 1:
            top_card = game_state.deck.discard[-1]
            reshuffle = game_state.deck.discard[:-1]
            game_state.deck.discard = [top_card]
            
            shuffle(reshuffle)
            game_state.deck.pile = reshuffle