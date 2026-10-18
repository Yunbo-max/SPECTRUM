def find_kth(arr1, arr2, k):
    # Initialize pointers for both arrays
    i, j = 0, 0
    # Iterate until we find the kth element
    while i < len(arr1) and j < len(arr2):
        if arr1[i] < arr2[j]:
            i += 1
        else:
            j += 1
        k -= 1
    # If k is 0, return the last element found
    if k == 0:
        return arr1[i-1] if i > 0 else arr2[j-1]
    # If k is greater than 0, return the next element in the array with more elements
    elif i < len(arr1):
        return arr1[i]
    else:
        return arr2[j]