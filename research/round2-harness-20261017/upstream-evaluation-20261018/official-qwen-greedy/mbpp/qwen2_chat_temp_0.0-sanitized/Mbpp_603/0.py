def get_ludic(n):
    """
    Generate a list of all lucid numbers less than or equal to n.
    A lucid number is a number that is the sum of two distinct prime numbers.
    
    Parameters:
    n (int): The upper limit for generating lucid numbers.
    
    Returns:
    list: A list of lucid numbers.
    """
    def is_prime(num):
        """Check if a number is prime."""
        if num <= 1:
            return False
        for i in range(2, int(num**0.5) + 1):
            if num % i == 0:
                return False
        return True
    
    lucid_numbers = []
    for i in range(2, n + 1):
        for j in range(i + 1, n + 1):
            if is_prime(i) and is_prime(j) and i + j <= n:
                lucid_numbers.append(i + j)
    return lucid_numbers