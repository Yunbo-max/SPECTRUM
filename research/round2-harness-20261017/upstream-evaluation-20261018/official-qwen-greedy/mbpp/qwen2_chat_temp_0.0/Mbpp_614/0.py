def cummulative_sum(tuple_list):
    # Initialize the sum to 0
    total_sum = 0
    # Iterate through each tuple in the list
    for tup in tuple_list:
        # Add the sum of the current tuple to the total sum
        total_sum += sum(tup)
    # Return the total sum
    return total_sum