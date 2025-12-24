import pandas as pd
import json
import os
import sys

INPUT_FILE = os.path.abspath('data/processed/search_db.csv')
OUTPUT_FILE = os.path.abspath('data/processed/ingredients_trie.json')
ID_COL = 'id'
INGREDIENTS_COL = 'ingredients_serialized'
SEPARATOR = ';'

def get_file_mtime(filepath):
    """Returns the modification time of a file."""
    try:
        return os.path.getmtime(filepath)
    except OSError:
        return 0

def add_to_trie(trie, word, doc_id):
    """
    Inserts a word into the trie and adds the doc_id to the leaf node's set.
    """
    node = trie
    for char in word.lower().strip():
        if char not in node:
            node[char] = {}
        node = node[char]
    if "__ids__" not in node:
        node["__ids__"] = set()
    node["__ids__"].add(doc_id)

def set_default(obj):
    """Helper to serialize sets to lists for JSON."""
    if isinstance(obj, set):
        return list(obj)
    raise TypeError

def generate_ingredients_trie():
    input_mtime = get_file_mtime(INPUT_FILE)
    output_mtime = get_file_mtime(OUTPUT_FILE)

    if output_mtime > input_mtime:
        print(f"[{OUTPUT_FILE}] is up to date. Skipping generation.")
        return

    print(f"Source data changed or output missing. Generating Trie...")
    try:
        df = pd.read_csv(INPUT_FILE, usecols=[ID_COL, INGREDIENTS_COL])
    except FileNotFoundError:
        print(f"Error: {INPUT_FILE} not found.")
        sys.exit(1)
    trie_root = {}
    for doc_id, ingredients_str in zip(df[ID_COL], df[INGREDIENTS_COL]):
        if pd.isna(ingredients_str):
            continue
        ingredients = str(ingredients_str).split(SEPARATOR)
        
        for ingredient in ingredients:
            if ingredient.strip():
                add_to_trie(trie_root, ingredient, doc_id)
    print(f"Saving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(trie_root, f, default=set_default, separators=(',', ':'))
    
    print("Done.")

if __name__ == "__main__":
    generate_ingredients_trie()
