def is_Sub_Array(arr1, arr2):
    # Check if the length of arr1 is greater than arr2
    if len(arr1) > len(arr2):
        return False
    # Iterate through arr1
    for i in range(len(arr1)):
        # Check if the current element of arr1 matches the first element of arr2
        if arr1[i] == arr2[0]:
            # Check if the remaining elements of arr1 match the remaining elements of arr2
            if arr1[i:i+len(arr2)] == arr2:
                return True
    return False