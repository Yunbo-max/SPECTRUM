def last(arr, x):
    # Initialize the start and end pointers
    start = 0
    end = len(arr) - 1
    
    # Perform binary search
    while start <= end:
        mid = (start + end) // 2
        
        # If the middle element is equal to x, move the end pointer to the left
        if arr[mid] == x:
            start = mid + 1
        # If the middle element is greater than x, move the end pointer to the left
        elif arr[mid] > x:
            end = mid - 1
        # If the middle element is less than x, move the start pointer to the right
        else:
            start = mid + 1
    
    # Return the start pointer, which will be the last position of x
    return start