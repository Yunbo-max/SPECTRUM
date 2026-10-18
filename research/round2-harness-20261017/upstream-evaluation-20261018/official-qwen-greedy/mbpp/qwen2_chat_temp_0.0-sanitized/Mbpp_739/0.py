def find_Index(n):
    # Initialize the smallest triangular number
    smallest_triangular = 1
    # Initialize the count of digits
    count = 1
    # Loop until the count of digits is equal to n
    while count < n:
        # Calculate the next triangular number
        smallest_triangular += count
        # Increment the count of digits
        count += 1
    # Return the index of the smallest triangular number
    return smallest_triangular