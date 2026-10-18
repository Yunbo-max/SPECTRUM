def sum_in_range(l, r):
    # Initialize the sum to 0
    total_sum = 0
    # Iterate through the range from l to r
    for num in range(l, r + 1):
        # Check if the number is odd
        if num % 2 != 0:
            # Add the odd number to the total sum
            total_sum += num
    # Return the total sum of odd numbers
    return total_sum