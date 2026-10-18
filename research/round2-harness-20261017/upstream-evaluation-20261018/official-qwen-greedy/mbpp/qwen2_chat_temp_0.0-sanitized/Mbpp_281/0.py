def all_unique(lst):
    """
    Check if all elements in the given list are unique.

    Args:
    lst (list): The list to check.

    Returns:
    bool: True if all elements are unique, False otherwise.
    """
    return len(lst) == len(set(lst))