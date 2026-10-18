def sum_Of_Subarray_Prod(arr):
    n = len(arr)
    total_sum = 0
    for i in range(n):
        for j in range(i, n):
            total_sum += arr[i] * arr[j]
    return total_sum