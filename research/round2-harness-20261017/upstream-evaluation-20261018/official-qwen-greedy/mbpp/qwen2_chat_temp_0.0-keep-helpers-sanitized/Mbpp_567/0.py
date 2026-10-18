def issort_list(lst):
    """
    Check if the given list is sorted in ascending order.

    Args:
    lst (list): The list to check.

    Returns:
    bool: True if the list is sorted, False otherwise.
    """
    # Iterate through the list and compare each element with the next one
    for i in range(len(lst) - 1):
        # If the current element is greater than the next one, the list is not sorted
        if lst[i] > lst[i + 1]:
            return False
    # If the loop completes without finding any unsorted pair, the list is sorted
    return True