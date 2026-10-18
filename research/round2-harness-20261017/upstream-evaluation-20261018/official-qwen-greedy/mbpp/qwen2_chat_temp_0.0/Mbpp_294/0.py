def max_val(heterogeneous_list):
    # Initialize the maximum value to the first element of the list
    max_val = heterogeneous_list[0]
    # Iterate through each element in the list
    for item in heterogeneous_list:
        # Update max_val if the current item is greater than max_val
        if item > max_val:
            max_val = item
    # Return the maximum value found
    return max_val