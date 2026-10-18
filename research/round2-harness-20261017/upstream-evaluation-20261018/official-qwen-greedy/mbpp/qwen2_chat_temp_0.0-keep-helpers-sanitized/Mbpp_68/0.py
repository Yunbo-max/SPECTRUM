def is_Monotonic(arr):
    # Check if the array is non-decreasing
    if all(arr[i] <= arr[i+1] for i in range(len(arr)-1)):
        return True
    # Check if the array is non-increasing
    elif all(arr[i] >= arr[i+1] for i in range(len(arr)-1)):
        return True
    else:
        return False