from dataclasses import replace
from dataclasses import dataclass
from enum import Enum
from random import shuffle, choice

# Enum for storing card colors 
# (RGBY + Black for power cards.)
class Color(Enum):
    RED = "Red"
    YELLOW = "Yellow"
    GREEN = "Green"
    BLUE = "Blue"   
    BLACK = "Black"
    
# Enum for storing card values
# (0 through 9, and power cards.)
class Value(Enum):
    ZERO = "0"
    ONE = "1"
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    
    SKIP = "Skip"
    REVERSE = "Reverse"
    DRAW_TWO = "Draw Two"
    DRAW_FOUR = "Draw Four"
    WILD = "Wild"
    
# Debug text color ANSI codes.
class TextColor(Enum):
    RED = 31
    YELLOW = 33
    GREEN = 32
    BLUE = 34
    BLACK = 39
    
# Represents one card in the game, which is assigned a 
# color and a value. (all power cards are assigned Color.BLACK,
# but it is easier to track it here anyway)
@dataclass(frozen=True, eq=True)
class Card:
    color: Color
    value: Value
    
    # Formats the card for debugging purposes into a colored number
    # or a power card explanation using the Color + Value enums.
    def format_card(self, ansi_code: int) -> str:
        if self.color == Color.BLACK:
            return f"\x1b[1m{self.value.value}\x1b[0m"
        
        # Some string formatting magic I found on the internet
        return f"\x1b[{ansi_code};49;1m{self.color.value}\x1b[0m {self.value.value}"

    def __str__(self) -> str:
        ansi_code = TextColor[self.color.name].value
        return self.format_card(ansi_code)

# Represents the decks available to the players, separated into
# the draw pile and the discard pile.
class Deck:
    # The cards available to be drawn. NOT public information.
    pile: list[Card]
    
    # The cards that have already been played.
    # The top card is what the current player must compare to.
    discard: list[Card]
    
    # All of the cards that could theoretically exist,
    # as if they all got taken out of the box.
    full_deck: list[Card]

    # Fills the draw pile with all of the cards in play,
    # according to the official UNO game rules by Mattel. 
    def __init__(self):
        self.pile = []
        self.discard = []
        
        for color in Color:
            if color == Color.BLACK:
                for _ in range(0, 4):
                    for value in [Value.WILD, Value.DRAW_FOUR]:
                        self.pile.append(Card(color, value))
    
            else: 
                self.pile.append(Card(color, Value.ZERO))
                
                for _ in range(0, 2):
                    for value in Value:
                        if value in [Value.ZERO, Value.WILD, Value.DRAW_FOUR]:
                            continue
                        
                        self.pile.append(Card(color, value))
        
        # Save the current pile contents as the full deck.
        self.full_deck = self.pile.copy()
        self.shuffle()
        
        # Adds the top card of the draw pile to discard.
        # (functionally starts the game)
        self.discard.append(self.pile.pop())
        
    # Shuffles the draw pile
    def shuffle(self):
        shuffle(self.pile)
        
    # Draws a card. If there's nothing to draw,
    # shuffle the discard, set to a new pile, then draw the top card.
    def draw(self, debug: bool = False) -> Card:
        if not self.pile:
            self.pile = self.discard
            self.shuffle()
            
            self.discard = []
            self.discard.append(self.pile.pop())
            
            if debug:
                print("Deck reshuffled.")
        
        return self.pile.pop()
        
    # Checks to see if a given card is "valid", e.g.
    # color match / symbol match / Black card.
    def can_play_card(self, card: Card) -> bool:
        top_card = self.discard[0]
        return card.color == top_card.color or card.value == top_card.value or card.color == Color.BLACK
    
    # Adds the given card to the top of the discard pile.
    def play_to_pile(self, card_played: Card):
        self.discard.insert(0, card_played)
        
    # Creates a new deck with the given full deck, 
    # draw pile, and discard pile states
    @staticmethod
    def custom_deck(full_deck: list[Card], pile: list[Card], discard: list[Card]):
        new_deck: Deck = Deck()
        new_deck.full_deck = full_deck
        new_deck.pile = pile
        new_deck.discard = discard
        
        return new_deck

    def __str__(self) -> str:
        out = "DRAW:\n"
        for card in self.pile:
            out += f"{str(card)}\n"
            
        out += "\n\nDISCARD:\n"
        for card in self.discard:
            out += f"{str(card)}\n"
        
        return out

# Represents a player at the table, given their name and
# the cards they currently have in their hand
class Player:
    name: str
    hand: list[Card]
    
    def __init__(self, name: str):
        self.name = name
        self.hand: list[Card] = []
        
    # Shuffles the player's hand.
    def shuffle_hand(self) -> None:
        shuffle(self.hand)
        
    # Adds the given card into their hand.
    def draw_card(self, card: Card):
        self.hand += [card]
        
    # Prints out the contents of the player's hand
    # as if it were a deck.
    def show_hand(self) -> None:
        print(f"{self.name}'s hand: ({self.hand.__len__()} cards)\n")
        for card in self.hand:
            print(str(card))
            
        print()
        
    # Attempts to play the first card in their hand that is playable
    # in the current game state, and if it exists, that card is returned.
    def play_card(self, g_state: 'GameState') -> Card | bool:
        for card in self.hand:
            playable = g_state.deck.can_play_card(card)
            if playable:
                self.hand.remove(card)
                return card
            
        return False
    
    # Randomly selects a color.
    def choose_color(self):
        return choice([Color.RED, Color.YELLOW, Color.GREEN, Color.BLUE])
    
    # Creates a new player given the name and their current hand.
    def dummy_player(self):
        new_player = Player(self.name)
        new_player.hand = self.hand.copy()
        
        return new_player

# Represents a possible state of a game of UNO.
class GameState:
    # Player data.
    players: list[Player]
    player_count: int
    
    # Deck data.
    deck: Deck
    
    # Turn data.
    turn: int
    turn_counter: int
    direction: int # Used to control the movement of play (-1 for left, 1 for right)
    
    # Statistics and debug values.
    game_end: bool
    debug: bool

    # Initializes a game of UNO with the given parameters.
    def __init__(self, players: list[Player] = [], debug: bool = False, turn: int = 0, direction: int = 1, game_end: bool = False):
        self.deck = Deck()
        self.deck.shuffle()
        
        self.players = players
        self.player_count = len(players)
        
        self.turn = turn
        self.turn_counter = 0
        
        self.direction = direction
        self.game_end = game_end
        self.debug = debug

        # Each player draws 7 cards at the start of the game.
        for _ in range(0, 7):
            for player in players:
                player.draw_card(self.deck.draw())

    # Moves to the next player, looping around if the
    # turn order moves to the start / end of the "array" of players.
    def next_player(self) -> int:
        self.turn += self.direction
        self.turn = 0 if self.turn > self.player_count - 1 else self.turn
        self.turn = self.player_count - 1 if self.turn < 0 else self.turn

        return self.turn
    
    # Attempts to process the given turn by checking if the move is
    # valid and then updating the information accordingly depending on
    # the response caused by playing that given card
    def process_turn(self) -> Player:
        current_player = self.players[self.turn]
        card_played = current_player.play_card(self)

        if type(card_played) == Card:
            self.deck.play_to_pile(card_played)

            if self.debug:
                print(f"{current_player.name} plays {str(card_played)}.")
            
            match card_played.value:
                # Reverse flips the direction value.
                case Value.REVERSE:
                    self.direction *= -1
                
                # Running next_player here increases the overall
                # turn counter by +/-2 in either direction, so someone
                # is being jumped over when we increment at the bottom.
                case Value.SKIP:
                    turn = self.next_player()
                
                # Add two cards to the next player's hand, then skip them.
                case Value.DRAW_TWO:
                    next = self.next_player()
                    
                    for _ in range(2):
                        self.players[next].draw_card(self.deck.draw())
                        
                    turn = self.next_player()
                
                case x if x in [Value.WILD, Value.DRAW_FOUR]:
                    # Change the color of the top card of the discard pile.
                    new_color = current_player.choose_color()
                    self.deck.discard[0] = replace(self.deck.discard[0], color=new_color)
                    
                    if self.debug:
                        print(f"{current_player.name} changes color to {new_color.value}.")
                        
                    # If this is a Draw Four, add four cards to the next player's hand, then skip themn.
                    if card_played == Value.DRAW_FOUR:
                        next = self.next_player()
                        
                        for _ in range(0, 4):
                            self.players[next].draw_card(self.deck.draw())
                            
                        turn = self.next_player()
        
        # If the current player has run out of cards, they win! : D
        if current_player.hand.__len__() == 0:
            self.game_end = True
            
        # If the current player cannot play a card, then they draw.
        # (in official UNO, you draw once and pass)
        if card_played == False:
            if self.debug:
                print(f"{current_player.name} draws.")
                
            current_player.draw_card(self.deck.draw())
            
        self.turn = self.next_player()
        self.turn_counter += 1

        return current_player
    
    def simulate_turn(self, card_played: Card) -> 'GameState':
        new_game_state = GameState(
            [player.dummy_player() for player in self.players], 
            self.debug, 
            self.turn, 
            self.direction, 
            self.game_end
        )
        
        current_player = new_game_state.players[new_game_state.turn]

        if type(card_played) == Card:
            new_game_state.deck.play_to_pile(card_played)
            
            # Analyze card behavior similar to process_turn.
            match card_played.value:
                case Value.REVERSE:
                    new_game_state.direction *= -1
                
                case Value.SKIP:
                    new_game_state.turn = new_game_state.next_player()
                
                case Value.DRAW_TWO:
                    next = new_game_state.next_player()
                    
                    for _ in range(2):
                        new_game_state.players[next].draw_card(new_game_state.deck.draw())
                        
                    new_game_state.turn = new_game_state.next_player()
                
                case x if x in [Value.WILD, Value.DRAW_FOUR]:
                    new_color = current_player.choose_color()
                    new_game_state.deck.discard[0] = replace(new_game_state.deck.discard[0], color=new_color)
                    
                    if card_played == Value.DRAW_FOUR:
                        next = new_game_state.next_player()
                        for _ in range(0, 4):
                            new_game_state.players[next].draw_card(new_game_state.deck.draw())
                            
                        new_game_state.turn = new_game_state.next_player()
            
        if current_player.hand.__len__() == 0:
            new_game_state.game_end = True
            
        if card_played == False:
            current_player.draw_card(new_game_state.deck.draw())
        
        # Return the updated game state.
        new_game_state.turn = new_game_state.next_player()
        new_game_state.turn_counter += 1

        return new_game_state
    
    # Comparison and output methods.
    def __str__(self):
        return f"""
            Player hands: {[player.hand for player in self.players]} ; 
            Turn: {self.turn} ; Direction: {self.direction} ; 
            Draw Pile Size : {self.deck.pile.__len__()}"""
    
    def __eq__(self, other):
        if isinstance(other, GameState):
            return self.__str__() == other.__str__()
        else:
            return False
        
    def __hash__(self):
        return hash(self.__str__())