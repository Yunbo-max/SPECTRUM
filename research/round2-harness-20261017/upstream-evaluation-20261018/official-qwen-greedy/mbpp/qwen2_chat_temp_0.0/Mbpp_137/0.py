import math

def zero_count(arr):
    """
    Calculate the ratio of zeroes to non-zeroes in an array of integers.
    
    Parameters:
    arr (list): A list of integers.
    
    Returns:
    float: The ratio of zeroes to non-zeroes in the array.
    """
    zero_count = sum(1 for num in arr if num == 0)
    non_zero_count = len(arr) - zero_count
    if non_zero_count == 0:
        return 0
    return zero_count / non_zero_count