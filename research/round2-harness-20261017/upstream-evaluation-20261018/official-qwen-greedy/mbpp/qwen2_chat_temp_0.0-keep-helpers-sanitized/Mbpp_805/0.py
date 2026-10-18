def max_sum_list(list_of_lists):
    # Initialize the maximum sum to a very small number
    max_sum = float('-inf')
    # Initialize the list that will store the list with the maximum sum
    max_list = []
    
    # Iterate through each list in the list of lists
    for sublist in list_of_lists:
        # Calculate the sum of the current sublist
        current_sum = sum(sublist)
        # If the current sum is greater than the maximum sum found so far
        if current_sum > max_sum:
            # Update the maximum sum and the list with the maximum sum
            max_sum = current_sum
            max_list = sublist
    
    # Return the list with the maximum sum
    return max_list