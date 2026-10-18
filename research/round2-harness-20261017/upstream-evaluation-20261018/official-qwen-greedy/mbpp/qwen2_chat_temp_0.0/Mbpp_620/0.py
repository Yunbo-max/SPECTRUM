def largest_subset(nums):
    # Sort the list in ascending order
    nums.sort()
    # Initialize the size of the largest subset
    size = 0
    # Initialize the current subset size
    current_size = 0
    # Iterate through the sorted list
    for i in range(len(nums)):
        # If the current number is divisible by the previous number in the subset
        if nums[i] % nums[i-1] == 0:
            # Increment the current subset size
            current_size += 1
        else:
            # Update the size of the largest subset if the current subset is larger
            size = max(size, current_size)
            # Reset the current subset size to 1
            current_size = 1
    # Update the size of the largest subset one last time
    size = max(size, current_size)
    return size