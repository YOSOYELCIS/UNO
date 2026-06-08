from uno import *
from collections import Counter

class MDP_Agent(Player):
    """
    The MDP Agent maintains and updates a distribution every turn based on the discard pile and its own hand expressing the probabilities of cards in other players' hands. It then uses that distribution to predict future turns, choosing the action (which card to play) with the highest expected utility.
    """
    name: str
    hand: list[Card]
    discount_factor: float
    survival_reward: int
    draw_penalty: int
    win_reward: int
    loss_penalty: int
    hand_size_penalty: int
    lowest_opponent_hand_size_reward: int
    
    def __init__(self, name: str, discount_factor: float = 0.75, survival_reward: int = 20, draw_penalty: int = -10, win_reward: int = 100, loss_penalty: int = -100, hand_size_penalty: int = 1, lowest_opponent_hand_size_reward: int = 2):
        """Modified init allows instantiating the class with special reward/penalty values to support fine tuning"""
        self.name = name
        self.hand: list[Card] = []
        self.discount_factor = discount_factor
        self.survival_reward = survival_reward
        self.draw_penalty = draw_penalty
        self.win_reward = win_reward
        self.loss_penalty = loss_penalty
        self.hand_size_penalty = hand_size_penalty
        self.lowest_opponent_hand_size_reward = lowest_opponent_hand_size_reward

    def play_card(self, g_state: GameState) -> Card | bool:
        playable_cards = [card for card in self.hand if g_state.deck.can_play_card(card)]
        
        if not(playable_cards):
            return False  # If we can't play any cards, draw
        elif len(playable_cards) == 1:
            return playable_cards[0] # If we can only play one card, play that card
        
        expected_values = {card: 0 for card in playable_cards}
        for card in playable_cards:
            expected_values[card] = self.calc_expected_value(card, g_state)
        pass

    def card_distribution(self, deck: Deck) -> dict[Card, float]:
        """
        Produces a normalized distribution of cards to probabilities based on what cards are either in the pile or opponents' hands
        """
        possibly_in_opponents_hand = [card for card in deck.full_deck if card not in self.hand + deck.discard]
        distribution: dict[Card, float]
        distribution = dict(Counter(possibly_in_opponents_hand))
        distribution = self.normalize(distribution)
        return distribution
    
    def play_distribution(self, game_state: GameState, hand_dist: dict[Card, float], top_card_dist: dict[Color, float]) -> dict[Card, float]:
        """
        Produces a normalized distribution of cards an opponent might play based on the distribution of cards it might have in its hand and the distribution of what card is on the top of the deck
        """
        pass

    def card_distr_to_color_distr(self, card_distr: dict[Card, float]) -> dict[Color, float]:
        """
        Takes a card distribution and simplifies it to a color distribution
        """
        color_distr: dict[Color, float] = {color: 0 for color in Color}
        for card in card_distr:
            color_distr[card.color] += card_distr[card]
        color_distr = self.normalize(color_distr)
        return color_distr

    def normalize[A](self, distr: dict[A, float]) -> dict[A, float]:
        """
        Normalizes a distribution
        """
        total = sum(value for value in distr.values())
        normalized_dist = {key: value/total for key, value in distr.items()}
        return normalized_dist
    
    def reward(self, hand_length):
        """
        Calculates a reward for the current state based on hand length, whether the agent or an opponent has won, the size of the smallest opponent hand, etc.
        Currently only uses hand_length
        """
        if (hand_length == 0):
            return self.win_reward
        else:
            return self.survival_reward - hand_length*self.hand_size_penalty