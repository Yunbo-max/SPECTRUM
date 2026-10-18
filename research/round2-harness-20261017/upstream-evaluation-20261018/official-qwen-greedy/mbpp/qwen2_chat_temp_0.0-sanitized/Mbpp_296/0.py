def get_Inv_Count(arr):
    """
    Count the number of inversions in an array.
    
    Args:
    arr (list): The input array.
    
    Returns:
    int: The number of inversions in the array.
    """
    inv_count = 0
    n = len(arr)
    for i in range(n):
        for j in range(i + 1, n):
            if arr[i] > arr[j]:
                inv_count += 1
    return inv_count