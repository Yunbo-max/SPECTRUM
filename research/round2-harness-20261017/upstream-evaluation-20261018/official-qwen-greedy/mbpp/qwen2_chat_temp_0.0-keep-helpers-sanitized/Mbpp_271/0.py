def even_Power_Sum(n):
    # Initialize the sum to 0
    sum = 0
    # Loop through the first n even natural numbers
    for i in range(2, 2*n+1, 2):
        # Raise the number to the fifth power and add it to the sum
        sum += i**5
    # Return the final sum
    return sum