import pandas as pd
from mlxtend.frequent_patterns import association_rules

# Load frequent itemsets
frequent_itemsets = pd.read_csv('frequent_itemsets.csv', converters={'itemsets': eval})

# Generate association rules
rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=0.5, num_itemsets=len(frequent_itemsets))

# Save association rules to a CSV
rules.to_csv('association_rules.csv', index=False)

# Display sample rules
print("Sample Association Rules:")
print(rules.head())
