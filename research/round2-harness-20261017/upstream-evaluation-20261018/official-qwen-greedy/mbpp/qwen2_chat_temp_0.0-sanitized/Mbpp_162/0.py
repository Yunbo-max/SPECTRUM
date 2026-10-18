def sum_series(n):
    # Initialize the sum to 0
    total_sum = 0
    # Loop through the range from 0 to n // 2
    for i in range(n // 2):
        # Add the current term to the total sum
        total_sum += (n - 2 * i)
    # Return the total sum
    return total_sum