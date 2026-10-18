def max_sub_array_sum(nums, n):
    # Initialize the maximum sum to the first element of the list
    max_sum = nums[0]
    # Initialize the current sum to the first element of the list
    current_sum = nums[0]
    
    # Iterate through the list starting from the second element
    for i in range(1, n):
        # Update the current sum to be the maximum of the current element itself or the sum of the current element and the previous current sum
        current_sum = max(nums[i], current_sum + nums[i])
        # Update the maximum sum to be the maximum of the current sum or the maximum sum found so far
        max_sum = max(max_sum, current_sum)
    
    # Return the maximum sum found
    return max_sum