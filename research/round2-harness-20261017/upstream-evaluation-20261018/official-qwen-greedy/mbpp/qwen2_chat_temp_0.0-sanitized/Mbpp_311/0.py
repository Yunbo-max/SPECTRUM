def set_left_most_unset_bit(n):
    # Initialize the result to 0
    result = 0
    # Iterate through the bits of the number
    while n > 0:
        # If the least significant bit is unset (i.e., it is 0)
        if n & 1 == 0:
            # Set the leftmost unset bit
            result |= 1
            # Right shift the number to check the next bit
            n >>= 1
        else:
            # Right shift the number to check the next bit
            n >>= 1
    return result