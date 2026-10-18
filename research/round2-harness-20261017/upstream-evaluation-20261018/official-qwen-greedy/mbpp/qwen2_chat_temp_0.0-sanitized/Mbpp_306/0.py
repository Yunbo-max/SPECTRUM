def max_sum_increasing_subseq(arr, n, k, m):
    # Initialize a list to store the maximum sum of increasing subsequence ending at each index
    dp = [0] * (n + 1)
    
    # Iterate through each element in the array
    for i in range(1, n + 1):
        # Iterate through each element before the current element
        for j in range(i):
            # Check if the current element is greater than the element before it
            if arr[i - 1] > arr[j - 1]:
                # Update the maximum sum of increasing subsequence ending at the current index
                dp[i] = max(dp[i], dp[j] + arr[i - 1])
    
    # Return the maximum sum of increasing subsequence ending at the last index
    return dp[n]