def remove_odd(s):
    # Initialize an empty string to store the result
    result = ""
    # Iterate through each character in the input string
    for char in s:
        # Check if the character is even (i.e., not odd)
        if ord(char) % 2 == 0:
            # Append the even character to the result string
            result += char
    # Return the result string containing only even characters
    return result