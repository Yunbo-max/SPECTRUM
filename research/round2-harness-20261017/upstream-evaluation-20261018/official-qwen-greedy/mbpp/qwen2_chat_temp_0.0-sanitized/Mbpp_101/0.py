def kth_element(arr, k):
    # Check if the index k is within the valid range
    if k < 1 or k > len(arr):
        return "Index out of range"
    # Return the kth element in the array
    return arr[k-1]