def get_max_sum(n):
    # Base case: if n is 1, the maximum sum is 1
    if n == 1:
        return 1
    # Initialize the maximum sum to 0
    max_sum = 0
    # Iterate through possible divisors of n
    for i in range(1, n + 1):
        # Check if i is a divisor of n
        if n % i == 0:
            # Calculate the sum of the function values for the current divisor
            current_sum = get_max_sum(n // i)
            # Update the maximum sum if the current sum is greater
            max_sum = max(max_sum, current_sum)
    # Return the maximum sum found
    return max_sum