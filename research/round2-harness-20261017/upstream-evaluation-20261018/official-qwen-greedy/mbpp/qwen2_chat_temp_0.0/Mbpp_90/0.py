def len_log(words):
    # Initialize the maximum length to 0
    max_length = 0
    # Iterate through each word in the list
    for word in words:
        # Update the maximum length if the current word is longer
        if len(word) > max_length:
            max_length = len(word)
    # Return the maximum length found
    return max_length