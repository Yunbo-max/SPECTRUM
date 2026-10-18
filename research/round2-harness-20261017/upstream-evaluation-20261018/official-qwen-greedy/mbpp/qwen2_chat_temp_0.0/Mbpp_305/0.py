def start_withp(words):
    # Filter the list to include only words starting with 'p'
    filtered_words = [word for word in words if word.startswith('p')]
    # Return the first two words from the filtered list
    return filtered_words[:2]