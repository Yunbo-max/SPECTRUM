def odd_values_string(s):
    # Initialize an empty string to store the result
    result = ''
    # Iterate over the string using enumerate to get both index and character
    for index, char in enumerate(s):
        # Check if the index is even (0-based index)
        if index % 2 == 0:
            # Append the character to the result string
            result += char
    # Return the result string
    return result