def even_binomial_Coeff_Sum(n):
    # Initialize the sum to 0
    sum_even = 0
    # Iterate through the range from 0 to n
    for i in range(n + 1):
        # Calculate the binomial coefficient for the current index
        binomial_coeff = math.comb(n, i)
        # Check if the index is even
        if i % 2 == 0:
            # Add the binomial coefficient to the sum
            sum_even += binomial_coeff
    # Return the sum of even index binomial coefficients
    return sum_even