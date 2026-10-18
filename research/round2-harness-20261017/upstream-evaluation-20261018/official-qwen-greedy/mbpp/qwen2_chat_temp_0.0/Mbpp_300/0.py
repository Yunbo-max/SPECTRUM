import math

def count_binary_seq(n):
    """
    Calculate the number of binary sequences of length 2n where the sum of the first n bits is equal to the sum of the last n bits.
    
    Args:
    n (int): The length of the binary sequences.
    
    Returns:
    float: The count of such binary sequences.
    """
    # Calculate the number of ways to choose k bits out of n to be 1 (since the sum of the first n bits must equal the sum of the last n bits)
    # This is given by the binomial coefficient C(n, k)
    # The total number of binary sequences of length 2n is 2^(2n)
    # Therefore, the count of sequences where the sum of the first n bits is equal to the sum of the last n bits is C(n, n/2)
    if n % 2 == 0:
        return math.comb(n, n // 2)
    else:
        return 0.0
