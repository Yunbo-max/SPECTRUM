def capital_words_spaces(s):
    # Split the string into words
    words = s.split()
    # Join the words with spaces between them, but only if the word starts with a capital letter
    result = ' '.join(word if word[0].isupper() else word for word in words)
    return result