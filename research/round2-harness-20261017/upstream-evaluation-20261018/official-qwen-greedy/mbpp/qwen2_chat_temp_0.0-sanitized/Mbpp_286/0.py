def max_sub_array_sum_repeated(arr, n, k):
    # Calculate the sum of the original array
    original_sum = sum(arr)
    
    # If the original array sum is negative, return 0
    if original_sum < 0:
        return 0
    
    # Calculate the sum of the array after repeating k times
    repeated_sum = original_sum * k
    
    # Calculate the maximum subarray sum in the repeated array
    max_subarray_sum = max_subarray_sum_kadane(repeated_sum)
    
    return max_subarray_sum