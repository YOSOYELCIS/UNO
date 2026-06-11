from uno import *

# A command-line game handler so a player can play against
# the other agents at the table.
class UserAgent(Player):
    def __init__(self, name: str, interactive: bool = True):
        super().__init__(name)
        self.interactive = interactive

    # Attempts to play a card by first checking if there is an 
    # option to be made (if someone has no cards, or must draw,
    # they perform that action) then awaits the user's selection.
    def play_card(self, g_state: GameState) -> Card | bool:
        if not self.interactive:
            return self.auto_choose(g_state)

        self.print_turn_summary(g_state)

        playable_indices = self.playable_card_indices(g_state)
        
        if not playable_indices:
            print("You have no playable cards. Press Enter to draw.")
            input("> ")
            return False

        return self.ask_for_card(g_state, playable_indices)

    # Prompts the user to select an available color; 
    # used when a Wild / Draw Four is played.
    def choose_color(self) -> Color:
        if not self.interactive:
            return self.best_color_from_hand()

        color_options = [
            Color.RED,
            Color.YELLOW,
            Color.GREEN,
            Color.BLUE,
        ]

        print("\nChoose a color:")
        for index, color in enumerate(color_options, start=1):
            print(f"{index}. {color.value}")

        # Validates user input (index or color).
        while True:
            choice = input("> ").strip().lower()

            if choice.isdigit():
                color_index = int(choice) - 1
                if 0 <= color_index < len(color_options):
                    return color_options[color_index]

            for color in color_options:
                if choice == color.value.lower():
                    return color

            print("Please enter 1-4, or a color name.")

    # Automatically selects the next card 
    def auto_choose(self, g_state: GameState) -> Card | bool:
        playable_indices = self.playable_card_indices(g_state)
        if not playable_indices:
            return False

        chosen_card = self.hand[playable_indices[0]]
        self.hand.remove(chosen_card)
        return chosen_card

    # Asks the player to select a card from the display,
    # checking to see if the selection is a valid option before
    # returning the card's index.
    def ask_for_card(
        self,
        g_state: GameState,
        playable_indices: list[int],
    ) -> Card | bool:
        print("\nChoose a playable card number, or enter D to draw.")

        while True:
            choice = input("> ").strip().lower()
            if choice in ["d", "draw"]:
                return False

            if not choice.isdigit():
                print("Please enter a card number or D.")
                continue

            hand_index = int(choice) - 1
            if hand_index not in playable_indices:
                print("That card is not playable right now.")
                continue

            chosen_card = self.hand[hand_index]
            self.hand.remove(chosen_card)
            return chosen_card

    # Prints a summary of the previous turns prior to the user's turn.
    def print_turn_summary(self, g_state: GameState) -> None:
        top_card = g_state.deck.discard[0]

        print("\n" + "=" * 40)
        print(f"{self.name}'s turn")
        print(f"Turn: {g_state.turn_counter}")
        print(f"Top discard: {top_card}")
        print(f"Draw pile: {len(g_state.deck.pile)} cards")
        print("\nPlayers:")

        for index, player in enumerate(g_state.players):
            marker = " <- you" if player is self else ""
            print(f"- {player.name}: {len(player.hand)} cards{marker}")

        print("\nYour hand:")
        playable_indices = self.playable_card_indices(g_state)
        for index, card in enumerate(self.hand, start=1):
            playable_marker = "*" if index - 1 in playable_indices else " "
            print(f"{index:>2}. [{playable_marker}] {card}")

        print("\n* = playable")

    # Returns a list of the indices of cards in the user's hand
    # that are able to be played this turn.
    def playable_card_indices(self, g_state: GameState) -> list[int]:
        return [
            index
            for index, card in enumerate(self.hand)
            if g_state.deck.can_play_card(card)
        ]

    # Calculates the color that is most common in the player's hand.
    def best_color_from_hand(self) -> Color:
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

    def __deepcopy__(self, memo):
        copied_player = UserAgent(self.name, interactive=False)
        copied_player.hand = self.hand.copy()
        return copied_player