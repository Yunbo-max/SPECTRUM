def find_Odd_Pair(arr, n):
    # Initialize the count of odd pairs
    count = 0
    # Iterate through the array
    for i in range(n):
        for j in range(i+1, n):
            # Check if the XOR of the pair is odd
            if (arr[i] ^ arr[j]) % 2 != 0:
                count += 1
    return count