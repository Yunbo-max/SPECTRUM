def toggle_middle_bits(n):
    # Initialize the result to 0
    result = 0
    # Iterate over the bits of the number
    for i in range(1, n.bit_length() - 1):
        # Toggle the bit at position i
        result ^= (1 << i)
    # Return the result
    return result