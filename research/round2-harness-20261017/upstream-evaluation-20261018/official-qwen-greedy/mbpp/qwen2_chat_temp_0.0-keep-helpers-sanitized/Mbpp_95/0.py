def Find_Min_Length(list_of_lists):
    # Initialize the minimum length to a large number
    min_length = float('inf')
    # Iterate through each list in the list of lists
    for sublist in list_of_lists:
        # Update the minimum length if the current sublist is shorter
        if len(sublist) < min_length:
            min_length = len(sublist)
    # Return the minimum length found
    return min_length