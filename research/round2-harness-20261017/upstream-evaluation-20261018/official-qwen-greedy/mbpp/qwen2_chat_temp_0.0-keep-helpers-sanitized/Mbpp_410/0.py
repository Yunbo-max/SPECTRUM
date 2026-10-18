def min_val(heterogeneous_list):
    # Initialize the minimum value with the first element of the list
    min_val = heterogeneous_list[0]
    # Iterate through each element in the list
    for item in heterogeneous_list:
        # Update the minimum value if the current item is smaller
        if item < min_val:
            min_val = item
    # Return the minimum value found
    return min_val