def find_even_pair(nums):
    # Initialize a counter for even pairs
    even_pairs_count = 0
    
    # Iterate through the list of numbers
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            # Check if the XOR of the current pair is even
            if (nums[i] ^ nums[j]) % 2 == 0:
                # Increment the counter if the condition is met
                even_pairs_count += 1
    
    # Return the total count of even pairs
    return even_pairs_count