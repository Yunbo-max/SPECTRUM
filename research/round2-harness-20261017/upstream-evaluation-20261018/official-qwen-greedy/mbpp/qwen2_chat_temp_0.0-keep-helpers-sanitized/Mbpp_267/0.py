def square_Sum(n):
    # Initialize the sum to 0
    sum = 0
    # Loop through the first n odd natural numbers
    for i in range(1, 2*n, 2):
        # Add the square of the current odd number to the sum
        sum += i**2
    # Return the final sum
    return sum