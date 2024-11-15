from flask import Flask, jsonify, request
import random
import math
import csv
import requests
import logging
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure logging for better debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Clash Royale API base URL and API key
CLASH_ROYALE_API_BASE_URL = "https://api.clashroyale.com/v1/players/"
API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjhhNTUzZjNlLTBmMjktNDE2Ni1iMWFhLTA2NDM1NzZmMGY5MyIsImlhdCI6MTczMTY2NTc3MCwic3ViIjoiZGV2ZWxvcGVyLzhhNWU5OGFmLWQyMTYtN2VmOC0wM2RhLWFkZDQ0NGZlY2M1NyIsInNjb3BlcyI6WyJyb3lhbGUiXSwibGltaXRzIjpbeyJ0aWVyIjoiZGV2ZWxvcGVyL3NpbHZlciIsInR5cGUiOiJ0aHJvdHRsaW5nIn0seyJjaWRycyI6WyIxMDMuMjE2LjIxMi4yMjMiXSwidHlwZSI6ImNsaWVudCJ9XX0.MQ2BF3bn8aahm-p37zDHjICNBEnKoQVUPu9MSYjUOuGJ2pwCHGU-X9iQlPcxtPt_V5MHabjkwIb7cMCcqZZnlQ"  # Replace with your actual API key

# Define the Card class
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

    def score_balance(self):
        return self.damage + self.hitpoints

# Fitness function - Now includes elixir cost as well
def fitness(deck, optimization_type):
    if optimization_type == "balanced":
        # Balance the attack and defense, while considering the minimum elixir cost
        total_attack = sum(card.score_attack() for card in deck)
        total_defense = sum(card.score_defense() for card in deck)
        total_elixir = sum(card.elixir_cost for card in deck)
        logger.debug(f"Fitness calculation: Attack={total_attack}, Defense={total_defense}, Elixir={total_elixir}")
        # Prioritize balance, but also try to minimize elixir cost
        return (total_attack + total_defense) / total_elixir if total_elixir > 0 else 0
    return 0

# Mutation - Same as before, random card replacement
def mutate(deck, cards):
    index = random.randint(0, len(deck) - 1)
    new_card = random.choice(cards)
    while new_card in deck:
        new_card = random.choice(cards)
    deck[index] = new_card
    return deck

# Simulated Annealing
def simulated_annealing(cards, optimization_type, initial_temperature, cooling_rate, max_iterations):
    logger.debug("Starting simulated annealing")
    current_deck = random.sample(cards, 8)
    current_fitness = fitness(current_deck, optimization_type)
    best_deck = current_deck[:]
    best_fitness = current_fitness
    temperature = initial_temperature

    for iteration in range(max_iterations):
        new_deck = mutate(current_deck[:], cards)
        new_fitness = fitness(new_deck, optimization_type)

        if new_fitness > current_fitness:
            current_deck = new_deck
            current_fitness = new_fitness
        else:
            acceptance_probability = math.exp((new_fitness - current_fitness) / temperature)
            if random.random() < acceptance_probability:
                current_deck = new_deck
                current_fitness = new_fitness

        if current_fitness > best_fitness:
            best_deck = current_deck[:]
            best_fitness = current_fitness

        temperature *= cooling_rate
        if temperature < 1e-3:
            break

    logger.debug(f"Best fitness after annealing: {best_fitness}")
    return best_deck

# Fetch player cards from API
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

# Match cards with extended card data
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
        icon_url = player_card.get("iconUrls", {}).get("medium", "")  # Get the icon URL

        for csv_card in csv_cards:
            if csv_card["name"] == name:
                hitpoints_key = f"hitpoints{level}"
                damage_key = f"damage{level}"
                if hitpoints_key in csv_card and damage_key in csv_card:
                    try:
                        hitpoints = int(float(csv_card[hitpoints_key]))  # Safely convert to integer
                        damage = int(float(csv_card[damage_key]))      # Safely convert to integer
                    except ValueError:
                        logger.warning(f"Invalid data for card: {name}")
                        continue  # Skip this card if data is invalid

                    matched_cards.append(Card(
                        name=name,
                        current_level=int(level),
                        rarity=rarity,
                        elixir_cost=int(elixir_cost),
                        icon_url=icon_url,  # Include the icon URL in the Card object
                        hitpoints=hitpoints,
                        damage=damage
                    ))
    return matched_cards

@app.route('/get-deck/<player_tag>', methods=['GET'])
def get_deck(player_tag):
    logger.debug(f"Request received for player tag: {player_tag}")
    
    # Fetch player cards based on player_tag
    player_cards = fetch_player_cards(player_tag)
    if not player_cards:
        logger.error("Failed to fetch player data.")
        return jsonify({"error": "Failed to fetch player data."}), 500

    # Path to your card information CSV
    csv_file = "cardsInfo.csv"
    matched_cards = match_cards(player_cards, csv_file)
    if not matched_cards:
        logger.error("No matched cards found.")
        return jsonify({"error": "No matched cards found."}), 500

    # Optimize the deck with the "balanced" approach while minimizing elixir cost
    optimized_deck = simulated_annealing(
        matched_cards, "balanced", initial_temperature=100, cooling_rate=0.95, max_iterations=1000
    )

    # Calculate the average elixir cost
    total_elixir_cost = sum(card.elixir_cost for card in optimized_deck)
    avg_elixir_cost = total_elixir_cost / len(optimized_deck) if optimized_deck else 0

    # Prepare the response for the optimized deck
    optimized_deck_response = [
        {
            "name": card.name,
            "level": card.current_level,
            "rarity": card.rarity,
            "elixir_cost": card.elixir_cost,
            "damage": card.damage,
            "hitpoints": card.hitpoints,
            "icon_url": card.icon_url  # Include the icon_url in the response
        } for card in optimized_deck
    ]

    logger.debug(f"Optimized deck: {optimized_deck_response}")
    logger.debug(f"Average Elixir Cost: {avg_elixir_cost}")

    # Return the response with deck and average elixir cost
    return jsonify({"status": "success", "deck": optimized_deck_response, 'avg': round(avg_elixir_cost, 2)}), 200


if __name__ == "__main__":
    app.run(debug=True)