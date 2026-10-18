def move_zero(nums):
    """
    Move all zeroes to the end of the given list.
    """
    # Initialize pointers for non-zero and zero elements
    non_zero_index = 0
    zero_index = 0
    
    # Iterate through the list
    while zero_index < len(nums):
        # If the current element is not zero, move it to the non-zero position
        if nums[zero_index] != 0:
            nums[non_zero_index], nums[zero_index] = nums[zero_index], nums[non_zero_index]
            non_zero_index += 1
        # Move the zero pointer to the next position
        zero_index += 1
    
    return nums