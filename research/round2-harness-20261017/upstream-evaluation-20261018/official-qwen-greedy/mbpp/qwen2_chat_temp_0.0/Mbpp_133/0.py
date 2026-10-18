def sum_negativenum(nums):
    # Initialize the sum of negative numbers to 0
    sum_neg = 0
    # Iterate through each number in the list
    for num in nums:
        # Check if the number is negative
        if num < 0:
            # Add the negative number to the sum
            sum_neg += num
    # Return the sum of negative numbers
    return sum_neg