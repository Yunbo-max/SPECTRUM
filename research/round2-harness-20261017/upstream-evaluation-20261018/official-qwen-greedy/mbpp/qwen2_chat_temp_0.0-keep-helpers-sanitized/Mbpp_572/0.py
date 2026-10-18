def two_unique_nums(nums):
    # Convert the list of lists into a single list
    combined_list = [num for sublist in nums for num in sublist]
    # Use a set to remove duplicates
    unique_list = list(set(combined_list))
    # Return the list of unique numbers
    return unique_list