def max_Abs_Diff(arr):
    # Initialize the minimum and maximum elements to the first element of the array
    min_element = arr[0]
    max_element = arr[0]
    
    # Iterate through the array to find the minimum and maximum elements
    for num in arr:
        if num < min_element:
            min_element = num
        elif num > max_element:
            max_element = num
    
    # Calculate the maximum difference between the maximum and minimum elements
    max_diff = max_element - min_element
    
    # Return the maximum difference
    return max_diff