def max_sum(arr):
    n = len(arr)
    # Initialize the dp array for increasing subsequence
    increasing = [1] * n
    # Initialize the dp array for decreasing subsequence
    decreasing = [1] * n
    
    # Fill the increasing dp array
    for i in range(1, n):
        for j in range(i):
            if arr[i] > arr[j]:
                increasing[i] = max(increasing[i], increasing[j] + 1)
    
    # Fill the decreasing dp array
    for i in range(n - 2, -1, -1):
        for j in range(i + 1, n):
            if arr[i] > arr[j]:
                decreasing[i] = max(decreasing[i], decreasing[j] + 1)
    
    # Calculate the maximum sum of bitonic subsequence
    max_sum = 0
    for i in range(n):
        max_sum = max(max_sum, increasing[i] + decreasing[i] - 1)
    
    return max_sum