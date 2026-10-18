def max_length(list_of_lists):
    # Initialize the maximum length and the corresponding list
    max_length = 0
    max_list = []
    
    # Iterate through each sublist in the list of lists
    for sublist in list_of_lists:
        # Check if the current sublist's length is greater than the maximum length found so far
        if len(sublist) > max_length:
            # Update the maximum length and the corresponding list
            max_length = len(sublist)
            max_list = sublist
    
    # Return the maximum length and the corresponding list
    return (max_length, max_list)