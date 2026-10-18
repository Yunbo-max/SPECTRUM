def reverse_words(s):
    # Split the string into words
    words = s.split()
    # Reverse the list of words
    words.reverse()
    # Join the reversed words back into a string
    reversed_string = ' '.join(words)
    return reversed_string