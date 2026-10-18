def split_Arr(arr, n):
    # Split the list at the nth element
    first_part = arr[:n]
    second_part = arr[n:]
    # Add the first part to the end of the second part
    result = second_part + first_part
    return result