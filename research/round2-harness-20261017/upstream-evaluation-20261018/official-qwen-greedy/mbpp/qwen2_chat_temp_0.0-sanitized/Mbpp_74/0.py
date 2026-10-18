def is_samepatterns(patterns, sequence):
    # Check if the lengths of patterns and sequence are equal
    if len(patterns) != len(sequence):
        return False
    
    # Iterate through the patterns and sequence
    for i in range(len(patterns)):
        # Check if the current pattern matches the current sequence element
        if patterns[i] != sequence[i]:
            return False
    
    # If all patterns match the sequence, return True
    return True