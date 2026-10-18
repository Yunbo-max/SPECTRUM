def is_nonagonal(n):
    # Calculate the nth nonagonal number using the formula
    nth_nonagonal = (7 * n**2 - 2 * n) // 2
    return nth_nonagonal