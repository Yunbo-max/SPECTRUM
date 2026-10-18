def number_of_substrings(s):
    # Initialize the count of substrings
    count = 0
    # Iterate over the string to find all possible substrings
    for i in range(len(s)):
        for j in range(i + 1, len(s) + 1):
            # Increment the count for each substring found
            count += 1
    return count