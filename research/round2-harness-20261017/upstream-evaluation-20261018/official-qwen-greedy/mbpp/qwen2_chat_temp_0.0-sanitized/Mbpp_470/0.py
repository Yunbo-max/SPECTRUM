def add_pairwise(input_tuple):
    # Initialize an empty list to store the pairwise sums
    pairwise_sums = []
    # Iterate through the tuple, taking two elements at a time
    for i in range(len(input_tuple) - 1):
        # Calculate the sum of the current pair and append it to the list
        pairwise_sums.append(input_tuple[i] + input_tuple[i + 1])
    # Return the list of pairwise sums
    return pairwise_sums