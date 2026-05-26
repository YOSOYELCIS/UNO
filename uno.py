from dataclasses import dataclass
from enum import Enum
from random import shuffle

class Color(Enum):
    RED = "Red"
    YELLOW = "Yellow"
    GREEN = "Green"
    BLUE = "Blue"   
    BLACK = "Black"
    
class TextColor(Enum):
    RED = 31
    YELLOW = 33
    GREEN = 32
    BLUE = 34
    BLACK = 39
    
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
    
@dataclass(frozen=True, eq=True)
class Card:
    color: Color
    value: Value
    
    def format_card(self, ansi_code: int) -> str:
        if self.color == Color.BLACK:
            return f"\x1b[1m{self.value.value}\x1b[0m"
        
        return f"\x1b[{ansi_code};49;1m{self.color.value}\x1b[0m {self.value.value}"
    
    def __str__(self) -> str:
        ansi_code = TextColor[self.color.name].value
        return self.format_card(ansi_code)

class Deck:
    pile: list[Card]
    discard: list[Card]
    
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
        
        self.shuffle()
        self.discard.append(self.pile.pop())
        
    def draw(self, debug: bool = False) -> Card:
        if not self.pile:
            self.pile = self.discard
            self.shuffle()
            
            self.discard = []
            self.discard.append(self.pile.pop())
            
            if debug:
                print("Deck reshuffled.")
        
        return self.pile.pop()
        
    def shuffle(self):
        shuffle(self.pile)
        
    def can_play_card(self, card: Card) -> bool:
        top_card = self.discard[0]
        return card.color == top_card.color or card.value == top_card.value or card.color == Color.BLACK
        
    def __str__(self) -> str:
        out = "DRAW:\n"
        for card in self.pile:
            out += f"{str(card)}\n"
            
        out += "\n\nDISCARD:\n"
        for card in self.discard:
            out += f"{str(card)}\n"
        
        return out

class Player:
    name: str
    hand: list[Card]
    
    def __init__(self, name: str):
        self.name = name
        self.hand: list[Card] = []
        
    def draw_card(self, card: Card):
        self.hand += [card]
        
    def show_hand(self) -> None:
        print(f"{self.name}'s hand: {self.hand.__len__()}\n")
        for card in self.hand:
            print(str(card))
        print()
        
    def shuffle_hand(self) -> None:
        shuffle(self.hand)
        
    def play_card(self, card: Card, deck: Deck) -> bool:
        playable = deck.can_play_card(card)
        if playable:
            self.hand.remove(card)
            deck.discard.insert(0, card)
            
        return playable