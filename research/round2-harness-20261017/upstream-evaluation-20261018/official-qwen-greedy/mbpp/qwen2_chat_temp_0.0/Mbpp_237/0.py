def check_occurrences(tuples_list):
    # Create an empty dictionary to store the occurrences of each tuple
    occurrences = {}
    # Iterate over each tuple in the list
    for tup in tuples_list:
        # If the tuple is already in the dictionary, increment its count
        if tup in occurrences:
            occurrences[tup] += 1
        # If the tuple is not in the dictionary, add it with a count of 1
        else:
            occurrences[tup] = 1
    # Return the dictionary containing the occurrences of each tuple
    return occurrences