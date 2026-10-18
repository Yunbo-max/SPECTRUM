def is_polite(n):
    """
    Check if a number is polite.
    A polite number is a positive integer that can be expressed as the sum of two or more consecutive positive integers.
    """
    if n <= 1:
        return False
    for i in range(2, n):
        if n % i == 0:
            return False
    return True