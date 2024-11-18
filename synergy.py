import pandas as pd
import itertools
from collections import defaultdict
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, association_rules
import csv

# Load dataset
df = pd.read_csv('battles_dataset.csv')

# Step 1: Prepare transactions
def prepare_transactions(df):
    transactions = []
    for _, row in df.iterrows():
        # Combine Player 1 and Player 2 decks into a single transaction
        combined_deck = list(row[['p1_1', 'p1_2', 'p1_3', 'p1_4', 'p1_5', 'p1_6', 'p1_7', 'p1_8']].values) + \
                        list(row[['p2_1', 'p2_2', 'p2_3', 'p2_4', 'p2_5', 'p2_6', 'p2_7', 'p2_8']].values)
        transactions.append(combined_deck)
    return transactions

# Generate transactions
transactions = prepare_transactions(df)

# Save transactions to a CSV (optional)
with open('transactions.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerows(transactions)
print("Transaction dataset saved as 'transactions.csv'")

# Step 2: Generate frequent patterns using Apriori
# Convert transactions to a one-hot encoded DataFrame
te = TransactionEncoder()
te_array = te.fit(transactions).transform(transactions)
df_encoded = pd.DataFrame(te_array, columns=te.columns_)

# Apply Apriori algorithm
frequent_itemsets = apriori(df_encoded, min_support=0.1, use_colnames=True)

# Save frequent itemsets to a CSV
frequent_itemsets.to_csv('frequent_itemsets.csv', index=False)
print("Frequent itemsets saved as 'frequent_itemsets.csv'")

# Step 3: Generate association rules
rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1.0)

# Save association rules to a CSV
rules.to_csv('association_rules.csv', index=False)
print("Association rules saved as 'association_rules.csv'")

# Optional: Display some frequent itemsets and rules
print("\nSample Frequent Itemsets:")
print(frequent_itemsets.head())

print("\nSample Association Rules:")
print(rules.head())
