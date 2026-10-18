def power(a, b):
    # Initialize the result to 1
    result = 1
    # Loop 'b' times
    for _ in range(b):
        # Multiply the result by 'a'
        result *= a
    # Return the final result
    return result