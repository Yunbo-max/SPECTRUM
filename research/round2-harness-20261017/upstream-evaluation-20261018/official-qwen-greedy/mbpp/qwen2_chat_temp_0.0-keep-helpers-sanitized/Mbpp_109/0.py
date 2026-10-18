def odd_Equivalent(binary_string, rotations):
    # Initialize the count of numbers with odd values
    odd_count = 0
    
    # Iterate through each rotation
    for _ in range(rotations):
        # Rotate the binary string to the right by one position
        binary_string = binary_string[-1] + binary_string[:-1]
        
        # Check if the last character of the rotated string is '1'
        if binary_string[-1] == '1':
            # Increment the count if the last character is '1'
            odd_count += 1
    
    # Return the count of numbers with odd values
    return odd_count