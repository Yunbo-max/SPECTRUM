def highest_Power_of_2(n):
    """
    Find the highest power of 2 that is less than or equal to n.

    Args:
    n (int): The number to find the highest power of 2 for.

    Returns:
    int: The highest power of 2 less than or equal to n.
    """
    power = 1
    while power * 2 <= n:
        power *= 2
    return power