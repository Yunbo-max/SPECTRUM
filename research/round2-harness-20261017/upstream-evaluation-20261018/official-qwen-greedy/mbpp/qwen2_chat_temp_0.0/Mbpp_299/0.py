def max_aggregate(tuples_list):
    # Initialize the maximum aggregate to 0
    max_aggregate = 0
    # Iterate through each tuple in the list
    for name, score in tuples_list:
        # Update the maximum aggregate if the current score is greater
        if score > max_aggregate:
            max_aggregate = score
    # Return the tuple with the maximum aggregate
    return (name, max_aggregate)