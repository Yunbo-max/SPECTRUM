def right_insertion(arr, x):
    # Initialize the left and right pointers
    left, right = 0, len(arr) - 1
    
    # Perform binary search
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] < x:
            left = mid + 1
        else:
            right = mid - 1
    
    # Return the right insertion point
    return left