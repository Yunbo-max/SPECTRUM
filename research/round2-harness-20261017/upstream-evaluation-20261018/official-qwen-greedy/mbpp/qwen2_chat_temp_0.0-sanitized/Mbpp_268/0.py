def find_star_num(n):
    """
    Calculate the n'th star number.
    
    Args:
    n (int): The position of the star number in the sequence.
    
    Returns:
    int: The n'th star number.
    """
    return n * (4 * n - 3)