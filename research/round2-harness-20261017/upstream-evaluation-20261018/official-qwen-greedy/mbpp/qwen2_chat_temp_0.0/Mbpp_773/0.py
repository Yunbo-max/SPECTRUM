def occurance_substring(string, substring):
    # Initialize variables to store the position and count of occurrences
    position = 0
    count = 0
    
    # Loop through the string to find all occurrences of the substring
    while position < len(string):
        # Check if the current position matches the start of the substring
        if string[position:position+len(substring)] == substring:
            # Increment the count of occurrences
            count += 1
            # Update the position to the next character after the found substring
            position += len(substring)
        else:
            # Move to the next character in the string
            position += 1
    
    # Return the count of occurrences and the position of the first occurrence
    return (substring, count, position - 1) if count > 0 else None