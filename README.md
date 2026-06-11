# UNO

UNO simulation with a variety of user agents, as well as the option to play yourself.

## Available Agents

* **Default**: Plays the first valid card in its hand.
* **Shuffle**: Shuffles its hand each round, then acts like Default.
* **Power**: Always opts to play a Black card whenever possible, then attempts to play a match.
* **Wait**: Always opts to try and match first, then tries to play a Black card.

* **SimpleTreeAgent**: Uses a decision tree (as shown in the `diagrams` folder) to pick what to do by using a utility function to weigh certain decisions.
* **WeightedHeuristicAgent**: Two heuristic agents that have custom weighting to determine what to play next.
* **Expectimax**: Uses Expectimax predictions to find an outcome with a high maximized utility.
* **MDPAgent**: Uses Markov Decision Process techniques to analyze future game states and selects the card that has the highest chance of leading to an optimal outcome.
