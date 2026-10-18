def perfect_squares(start, end):
    # Initialize an empty list to store perfect squares
    perfect_squares_list = []
    # Loop through the range from start to end
    for num in range(start, end + 1):
        # Check if the number is a perfect square
        if int(num**0.5)**2 == num:
            # If it is, append it to the list
            perfect_squares_list.append(num)
    # Return the list of perfect squares
    return perfect_squares_list