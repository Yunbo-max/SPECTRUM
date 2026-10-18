def remove_length(s, k):
    # Split the string into words
    words = s.split()
    # Filter out words with k length
    filtered_words = [word for word in words if len(word) != k]
    # Join the filtered words back into a string
    result = ' '.join(filtered_words)
    return result