def max_occurrences(lst):
    # Create a dictionary to store the frequency of each item
    frequency = {}
    for item in lst:
        if item in frequency:
            frequency[item] += 1
        else:
            frequency[item] = 1
    
    # Find the item with the maximum frequency
    max_freq_item = max(frequency, key=frequency.get)
    
    return max_freq_item