import os
import json
import sys
import pandas as pd

class TrieManager:
    def __init__(self, source_csv, output_json, id_col, data_col, separator=';'):
        self.source_csv = os.path.abspath(source_csv)
        self.output_json = os.path.abspath(output_json)
        self.id_col = id_col
        self.data_col = data_col
        self.separator = separator
        self.trie_root = {}

        # 1. Ensure Trie exists and is up to date
        self._generate_trie_if_needed()
        
        # 2. Load the Trie into memory
        self._load_trie()

    def _get_file_mtime(self, filepath):
        try:
            return os.path.getmtime(filepath)
        except OSError:
            return 0

    def _add_to_trie(self, trie, word, doc_id):
        node = trie
        # strip and lower for consistent matching
        clean_word = word.lower().strip()
        if not clean_word:
            return

        for char in clean_word:
            if char not in node:
                node[char] = {}
            node = node[char]
        
        if "__ids__" not in node:
            node["__ids__"] = [] # Using list directly for JSON compatibility
        
        # Avoid duplicates in list if necessary, but list is faster for append
        if doc_id not in node["__ids__"]:
            node["__ids__"].append(doc_id)

    def _generate_trie_if_needed(self):
        input_mtime = self._get_file_mtime(self.source_csv)
        output_mtime = self._get_file_mtime(self.output_json)

        if output_mtime > input_mtime and output_mtime > 0:
            print(f"[{self.output_json}] is up to date. Skipping generation.")
            return

        print(f"Source changed or output missing. Generating Trie from {self.source_csv}...")
        
        try:
            # Only read necessary columns
            df = pd.read_csv(self.source_csv, usecols=[self.id_col, self.data_col])
        except (FileNotFoundError, ValueError) as e:
            print(f"Error reading CSV: {e}")
            self.trie_root = {}
            return

        temp_root = {}
        for doc_id, data_str in zip(df[self.id_col], df[self.data_col]):
            if pd.isna(data_str):
                continue
            
            # Split by separator (e.g. ingredients list)
            items = str(data_str).split(self.separator)
            
            for item in items:
                self._add_to_trie(temp_root, item, doc_id)

        # Save to JSON
        os.makedirs(os.path.dirname(self.output_json), exist_ok=True)
        with open(self.output_json, 'w', encoding='utf-8') as f:
            # separators=(',', ':') removes whitespace to make file smaller
            json.dump(temp_root, f, separators=(',', ':'))
        
        print("Trie generation complete.")

    def _load_trie(self):
        try:
            with open(self.output_json, 'r', encoding='utf-8') as f:
                self.trie_root = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print("Error: Could not load JSON trie.")
            self.trie_root = {}

    def search(self, prefix):
        """
        Returns a list of full words starting with 'prefix'.
        Returns empty list if input length < 1.
        """
        if not prefix or len(prefix) < 1:
            return []

        prefix = prefix.lower()
        node = self.trie_root
        
        # 1. Traverse to the end of the prefix
        for char in prefix:
            if char in node:
                node = node[char]
            else:
                return []
        
        # 2. Collect all words from this point
        results = []
        self._dfs(node, prefix, results)
        return results

    def _dfs(self, node, current_word, results):
        if "__ids__" in node:
            results.append(current_word)
        
        for char, child_node in node.items():
            if char != "__ids__":
                self._dfs(child_node, current_word + char, results)
