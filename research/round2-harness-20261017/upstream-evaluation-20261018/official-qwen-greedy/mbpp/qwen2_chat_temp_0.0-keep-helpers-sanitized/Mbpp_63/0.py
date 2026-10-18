def max_difference(pairs):
    # Initialize the maximum difference to negative infinity
    max_diff = float('-inf')
    # Iterate through each pair in the list
    for pair in pairs:
        # Calculate the difference between the two elements in the pair
        diff = pair[1] - pair[0]
        # Update the maximum difference if the current difference is greater
        if diff > max_diff:
            max_diff = diff
    # Return the maximum difference found
    return max_diff