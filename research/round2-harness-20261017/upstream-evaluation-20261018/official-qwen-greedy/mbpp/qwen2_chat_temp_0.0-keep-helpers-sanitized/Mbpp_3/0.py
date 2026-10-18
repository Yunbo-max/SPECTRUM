def is_not_prime(num):
    """
    Check if a number is not prime.
    
    Args:
    num (int): The number to check.
    
    Returns:
    bool: True if the number is not prime, False otherwise.
    """
    if num <= 1:
        return True
    for i in range(2, int(num**0.5) + 1):
        if num % i == 0:
            return True
    return False