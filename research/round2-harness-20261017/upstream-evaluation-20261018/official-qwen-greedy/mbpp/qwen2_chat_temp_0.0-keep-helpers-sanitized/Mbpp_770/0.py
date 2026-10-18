def odd_num_sum(n):
    # Initialize the sum to 0
    sum = 0
    # Loop through the first n odd natural numbers
    for i in range(1, 2*n, 2):
        # Add the fourth power of the current odd number to the sum
        sum += i**4
    # Return the total sum
    return sum