def sum_Of_product(n):
    # Initialize the sum to 0
    sum = 0
    # Iterate over the range from 0 to n-1
    for i in range(n):
        # Calculate the binomial coefficient for the current i
        binomial_coefficient = math.comb(n, i)
        # Multiply the binomial coefficient by the next binomial coefficient
        sum += binomial_coefficient * math.comb(n, i+1)
    # Return the final sum
    return sum