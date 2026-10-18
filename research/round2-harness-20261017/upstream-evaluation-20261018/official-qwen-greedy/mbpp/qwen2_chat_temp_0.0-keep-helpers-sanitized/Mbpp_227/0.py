def min_of_three(a, b, c):
    # Initialize the minimum with the first number
    min_num = a
    # Compare the second number with the current minimum
    if b < min_num:
        min_num = b
    # Compare the third number with the current minimum
    if c < min_num:
        min_num = c
    # Return the minimum number found
    return min_num