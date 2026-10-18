def sum_common_divisors(a, b):
    # Initialize the sum of common divisors
    sum_divisors = 0
    
    # Iterate through all numbers from 1 to the minimum of a and b
    for i in range(1, min(a, b) + 1):
        # Check if i is a divisor of both a and b
        if a % i == 0 and b % i == 0:
            # Add i to the sum of common divisors
            sum_divisors += i
    
    # Return the sum of common divisors
    return sum_divisors