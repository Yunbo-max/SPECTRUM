import re

def find_adverb_position(sentence):
    # Use regular expression to find all occurrences of adverbs
    adverbs = re.findall(r'\b\w+ly\b', sentence)
    # Find the positions of each adverb
    positions = [sentence.find(adverb) for adverb in adverbs]
    return positions, adverbs