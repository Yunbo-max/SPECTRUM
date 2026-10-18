def count_list(lists):
    # Initialize a counter to keep track of the number of lists
    count = 0
    # Iterate through each list in the given list of lists
    for sublist in lists:
        # Increment the counter for each sublist found
        count += 1
    # Return the total count of lists
    return count