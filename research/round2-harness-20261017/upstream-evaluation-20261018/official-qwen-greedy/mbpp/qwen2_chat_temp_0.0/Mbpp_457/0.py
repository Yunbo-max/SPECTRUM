def Find_Min(lst):
    # Initialize the minimum length to the length of the first sublist
    min_length = len(lst[0])
    # Initialize the sublist with the first sublist
    min_sublist = lst[0]
    # Iterate through the list of sublists
    for sublist in lst:
        # If the current sublist is shorter than the current minimum length
        if len(sublist) < min_length:
            # Update the minimum length and the sublist
            min_length = len(sublist)
            min_sublist = sublist
    # Return the sublist with the minimum length
    return min_sublist