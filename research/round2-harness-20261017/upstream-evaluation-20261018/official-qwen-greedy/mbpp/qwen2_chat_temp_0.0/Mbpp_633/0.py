def pair_xor_Sum(arr, n):
    # Initialize the sum to 0
    sum_xor = 0
    
    # Iterate through each pair of numbers in the list
    for i in range(n):
        for j in range(i+1, n):
            # Calculate the XOR of the current pair and add it to the sum
            sum_xor += (arr[i] ^ arr[j])
    
    # Return the total sum of XOR of all pairs
    return sum_xor