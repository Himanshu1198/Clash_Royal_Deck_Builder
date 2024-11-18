import requests
import csv
import random
from flask import Flask, request, jsonify
from deap import base, creator, tools
import logging
import pandas as pd
from deap.tools.emo import sortNondominated
from deap.tools.emo import assignCrowdingDist  # Use it only within fronts
from flask_cors import CORS

# Setup Flask app and logger
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Clash Royale API base URL and API key
CLASH_ROYALE_API_BASE_URL = "https://api.clashroyale.com/v1/players/"
API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjhhNTUzZjNlLTBmMjktNDE2Ni1iMWFhLTA2NDM1NzZmMGY5MyIsImlhdCI6MTczMTY2NTc3MCwic3ViIjoiZGV2ZWxvcGVyLzhhNWU5OGFmLWQyMTYtN2VmOC0wM2RhLWFkZDQ0NGZlY2M1NyIsInNjb3BlcyI6WyJyb3lhbGUiXSwibGltaXRzIjpbeyJ0aWVyIjoiZGV2ZWxvcGVyL3NpbHZlciIsInR5cGUiOiJ0aHJvdHRsaW5nIn0seyJjaWRycyI6WyIxMDMuMjE2LjIxMi4yMjMiXSwidHlwZSI6ImNsaWVudCJ9XX0.MQ2BF3bn8aahm-p37zDHjICNBEnKoQVUPu9MSYjUOuGJ2pwCHGU-X9iQlPcxtPt_V5MHabjkwIb7cMCcqZZnlQ"  # Replace with your API key

# Card class definition
class Card:
    def __init__(self, name, current_level, rarity, elixir_cost, icon_url, hitpoints, damage):
        self.name = name
        self.current_level = current_level
        self.rarity = rarity
        self.elixir_cost = elixir_cost
        self.icon_url = icon_url
        self.hitpoints = hitpoints
        self.damage = damage

    def score_attack(self):
        return self.damage

    def score_defense(self):
        return self.hitpoints


# Fetch player cards from Clash Royale API
def fetch_player_cards(player_tag):
    encoded_tag = player_tag.replace("#", "%23")
    url = f"{CLASH_ROYALE_API_BASE_URL}{encoded_tag}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    try:
        logger.debug(f"Fetching player cards for {player_tag}")
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            logger.debug("Successfully fetched player cards")
            return response.json().get("cards", [])
        else:
            logger.error(f"Failed to fetch player data: {response.status_code}")
            return None
    except requests.RequestException as e:
        logger.error(f"Error fetching data: {e}")
        return None


# Match player cards with extended data from CSV
def match_cards(player_cards, csv_file):
    logger.debug(f"Matching cards from player data with {csv_file}")
    with open(csv_file, mode="r", encoding="utf-8") as file:
        csv_cards = list(csv.DictReader(file))

    matched_cards = []
    for player_card in player_cards:
        name = player_card.get("name")
        level = player_card.get("level")
        elixir_cost = player_card.get("elixirCost", 0)
        rarity = player_card.get("rarity")
        icon_url = player_card.get("iconUrls", {}).get("medium", "")

        for csv_card in csv_cards:
            if csv_card["name"] == name:
                hitpoints_key = f"hitpoints{level}"
                damage_key = f"damage{level}"
                if hitpoints_key in csv_card and damage_key in csv_card:
                    try:
                        hitpoints = int(float(csv_card[hitpoints_key]))
                        damage = int(float(csv_card[damage_key]))
                    except ValueError:
                        logger.warning(f"Invalid data for card: {name}")
                        continue

                    matched_cards.append(Card(
                        name=name,
                        current_level=int(level),
                        rarity=rarity,
                        elixir_cost=int(elixir_cost),
                        icon_url=icon_url,
                        hitpoints=hitpoints,
                        damage=damage
                    ))
    return matched_cards


# Load frequent itemsets from CSV
def load_itemsets(file_path):
    df = pd.read_csv(file_path)
    df['itemsets'] = df['itemsets'].apply(eval)  # Convert string to frozenset
    return df

# Load association rules from CSV
def load_association_rules(file_path):
    df = pd.read_csv(file_path)
    df['antecedents'] = df['antecedents'].apply(eval)  # Convert string to frozenset
    df['consequents'] = df['consequents'].apply(eval)  # Convert string to frozenset
    return df


# Calculate synergy from frequent itemsets
def calculate_synergy(deck, itemset_df):
    deck_set = set(card.name for card in deck)
    synergy_score = 0
    for _, row in itemset_df.iterrows():
        if row['itemsets'].issubset(deck_set):
            synergy_score += row['support']
    return synergy_score


# Calculate synergy from association rules
def calculate_synergy_with_rules(deck, rules_df):
    deck_set = set(card.name for card in deck)
    synergy_score = 0
    for _, row in rules_df.iterrows():
        if row['antecedents'].issubset(deck_set):
            if row['consequents'].issubset(deck_set):
                synergy_score += row['confidence'] * row['lift'] * row['zhangs_metric']
    return synergy_score


def calculate_crowding_distance(population):
    """Assign crowding distance to individuals in the population."""
    # Sort individuals by non-domination rank
    fronts = sortNondominated(population, len(population), first_front_only=False)
    for front in fronts:
        tools.emo.assignCrowdingDist(front)

if not hasattr(creator, "FitnessMulti"):
    creator.create("FitnessMulti", base.Fitness, weights=(1.0, 1.0, -1.0, 1.0))  # Synergy, Damage, Elixir Penalty, Hitpoints

if not hasattr(creator, "Individual"):
    creator.create("Individual", list, fitness=creator.FitnessMulti)


def optimize_deck(card_pool):
    DECK_SIZE = 8
    POPULATION_SIZE = 20  # Reduced for quick testing
    GENERATIONS = 10      # Fewer generations for debugging
    ELIXIR_RANGE = (3.0, 4.5)

    # Load data
    itemset_df = load_itemsets("frequent_itemsets.csv")
    rules_df = load_association_rules("association_rules.csv")

    # Use pre-existing creator classes
    toolbox = base.Toolbox()
    toolbox.register("individual", tools.initIterate, creator.Individual, lambda: random.sample(card_pool, DECK_SIZE))
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    def evaluate_deck(individual):
     # Check if the deck contains duplicates
     if len(set(card.name for card in individual)) < len(individual):
         return -float('inf'), 0, 0, 0  # Invalid deck, assign a very low fitness score
     
     itemset_synergy = calculate_synergy(individual, itemset_df)
     rule_synergy = calculate_synergy_with_rules(individual, rules_df)
     total_synergy = itemset_synergy + rule_synergy

     damage = sum(card.score_attack() for card in individual)
     hitpoints = sum(card.score_defense() for card in individual)
     elixir_cost = sum(card.elixir_cost for card in individual)
     elixir_penalty = abs((elixir_cost / DECK_SIZE) - ((ELIXIR_RANGE[0] + ELIXIR_RANGE[1]) / 2))

     return total_synergy, damage, -elixir_penalty, hitpoints

    def mutate_unique(individual):
     card_names = {card.name for card in individual}  # Set of existing card names in the deck
     for i in range(len(individual)):
         if random.random() < 0.2:  # Mutation probability
             new_card = random.choice(card_pool)
             while new_card.name in card_names:  # Ensure uniqueness
                 new_card = random.choice(card_pool)
             individual[i] = new_card
             card_names.add(new_card.name)
     return individual,

    def crossover_unique(ind1, ind2):
     offspring1, offspring2 = tools.cxTwoPoint(ind1, ind2)
     unique_offspring1 = list({card.name: card for card in offspring1}.values())
     unique_offspring2 = list({card.name: card for card in offspring2}.values())

     # Fill missing cards from the pool to maintain deck size
     missing_count1 = DECK_SIZE - len(unique_offspring1)
     missing_count2 = DECK_SIZE - len(unique_offspring2)
     unused_cards1 = [card for card in card_pool if card.name not in {c.name for c in unique_offspring1}]
     unused_cards2 = [card for card in card_pool if card.name not in {c.name for c in unique_offspring2}]

     unique_offspring1.extend(random.sample(unused_cards1, missing_count1))
     unique_offspring2.extend(random.sample(unused_cards2, missing_count2))

     return unique_offspring1, unique_offspring2


    toolbox.register("evaluate", evaluate_deck)
    toolbox.register("mutate", mutate_unique)
    toolbox.register("mate", crossover_unique)
    toolbox.register("select", tools.selNSGA2)

    # Initialize population
    population = toolbox.population(n=POPULATION_SIZE)
    hof = tools.HallOfFame(1)

    # Evaluate initial population
    for ind in population:
        ind.fitness.values = toolbox.evaluate(ind)
    calculate_crowding_distance(population)

    # Optimization loop
    for gen in range(GENERATIONS):
        logger.debug(f"Generation {gen}: Starting evolution.")
        offspring = tools.selTournamentDCD(population, len(population))
        offspring = list(map(toolbox.clone, offspring))

        # Apply crossover and mutation
        for child1, child2 in zip(offspring[::2], offspring[1::2]):
            if random.random() < 0.7:
                toolbox.mate(child1, child2)
                del child1.fitness.values
                del child2.fitness.values
        for mutant in offspring:
            if random.random() < 0.2:
                toolbox.mutate(mutant)
                del mutant.fitness.values

        # Evaluate invalid fitness
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        for ind in invalid_ind:
            ind.fitness.values = toolbox.evaluate(ind)

        # Update population
        calculate_crowding_distance(offspring)
        population[:] = offspring

    hof.update(population)
    return hof[0]

@app.route('/get-deck/<player_tag>', methods=['GET'])
def get_deck(player_tag):
    logger.debug(f"Request received for player tag: {player_tag}")
    player_cards = fetch_player_cards(player_tag)
    if not player_cards:
        return jsonify({"error": "Failed to fetch player data."}), 500

    csv_file = "cardsInfo.csv"
    matched_cards = match_cards(player_cards, csv_file)
    if not matched_cards:
        return jsonify({"error": "No matched cards found."}), 500

    optimized_deck = optimize_deck(matched_cards)
    total_elixir_cost = sum(card.elixir_cost for card in optimized_deck)
    avg_elixir_cost = total_elixir_cost / len(optimized_deck) if optimized_deck else 0

    optimized_deck_response = [
        {
            "name": card.name,
            "level": card.current_level,
            "rarity": card.rarity,
            "elixir_cost": card.elixir_cost,
            "damage": card.damage,
            "hitpoints": card.hitpoints,
            "icon_url": card.icon_url
        } for card in optimized_deck
    ]

    print(optimized_deck_response)

    return jsonify({"status": "success", "deck": optimized_deck_response, 'avg': round(avg_elixir_cost, 2)}), 200


if __name__ == "__main__":
    app.run(debug=True)
