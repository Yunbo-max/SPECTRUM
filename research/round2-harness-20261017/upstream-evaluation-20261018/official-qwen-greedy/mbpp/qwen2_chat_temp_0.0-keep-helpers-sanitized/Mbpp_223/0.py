def is_majority(arr, n, element):
    # Check if the element is present in the array
    if element not in arr:
        return False
    
    # Count the occurrences of the element
    count = arr.count(element)
    
    # Check if the count is greater than n/2
    if count > n // 2:
        return True
    else:
        return False