import sys

def tuple_size(input_tuple):
    """
    Calculate the size in bytes of the given tuple.
    
    Args:
    input_tuple (tuple): The tuple whose size is to be calculated.
    
    Returns:
    int: The size in bytes of the tuple.
    """
    return sys.getsizeof(input_tuple)