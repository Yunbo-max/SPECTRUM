def first_non_repeating_character(s):
    # Create a dictionary to store the count of each character
    char_count = {}
    
    # Count the occurrences of each character in the string
    for char in s:
        if char in char_count:
            char_count[char] += 1
        else:
            char_count[char] = 1
    
    # Iterate through the string to find the first non-repeated character
    for char in s:
        if char_count[char] == 1:
            return char
    
    # If no non-repeated character is found, return None
    return None