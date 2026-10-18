def find_char_long(s):
    # Split the string into words
    words = s.split()
    # Filter words that are at least 4 characters long
    long_words = [word for word in words if len(word) >= 4]
    return long_words