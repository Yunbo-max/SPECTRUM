def find_min_diff(arr, n):
    # Initialize the minimum difference to a large number
    min_diff = float('inf')
    
    # Iterate through the array to find the minimum difference
    for i in range(n):
        for j in range(i+1, n):
            # Calculate the difference between the current pair of elements
            diff = abs(arr[i] - arr[j])
            # Update the minimum difference if the current difference is smaller
            if diff < min_diff:
                min_diff = diff
    
    # Return the minimum difference found
    return min_diff