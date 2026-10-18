def check_greater(arr, num):
    # Iterate through each element in the array
    for element in arr:
        # Check if the current element is greater than the given number
        if element > num:
            # If found, return False
            return False
    # If no element is greater than the given number, return True
    return True