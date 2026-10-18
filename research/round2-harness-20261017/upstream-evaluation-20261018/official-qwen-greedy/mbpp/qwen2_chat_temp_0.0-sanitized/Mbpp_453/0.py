def sumofFactors(n):
    # Initialize sum to 0
    sum = 0
    # Iterate through all numbers from 1 to n
    for i in range(1, n + 1):
        # Check if i is a factor of n
        if n % i == 0:
            # Check if i is even
            if i % 2 == 0:
                # Add i to the sum
                sum += i
    # Return the sum of even factors
    return sum