def long_words(n, words):
    # Use list comprehension to filter words longer than n characters
    return [word for word in words if len(word) > n]