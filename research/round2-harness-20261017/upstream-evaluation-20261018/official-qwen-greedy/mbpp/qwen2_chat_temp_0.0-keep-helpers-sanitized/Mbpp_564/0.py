def count_Pairs(arr, n):
    # Initialize the count of pairs
    count = 0
    # Iterate through the array
    for i in range(n):
        # Iterate through the array again
        for j in range(i+1, n):
            # Check if the elements are unequal
            if arr[i] != arr[j]:
                # Increment the count
                count += 1
    # Return the count of pairs
    return count