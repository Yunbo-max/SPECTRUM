def find_Parity(n):
    """
    This function checks if the parity of a given number is odd.
    
    Args:
    n (int): The number to check.
    
    Returns:
    bool: True if the parity is odd, False otherwise.
    """
    # Check if the number is odd by using the bitwise AND operation
    return n & 1