def sequence(n):
    # Initialize the first two numbers of the sequence
    a, b = 1, 1
    # Iterate to find the nth number
    for _ in range(2, n + 1):
        # Calculate the next number in the sequence
        a, b = b, a + b
    return b