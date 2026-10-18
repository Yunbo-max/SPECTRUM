def is_undulating(n):
    """
    Check if the given number is undulating or not.
    
    Args:
    n (int): The number to check.
    
    Returns:
    bool: True if the number is undulating, False otherwise.
    """
    # Convert the number to a string to easily access individual digits
    num_str = str(n)
    
    # Check if the number has at least 3 digits
    if len(num_str) < 3:
        return False
    
    # Check if the number is undulating
    for i in range(1, len(num_str) - 1):
        if num_str[i] != num_str[i - 1] and num_str[i] != num_str[i + 1]:
            return False
    
    return True