def odd_length_sum(arr):
    total_sum = 0
    for i in range(len(arr)):
        for j in range(i, len(arr)):
            if (j - i + 1) % 2 != 0:
                total_sum += sum(arr[i:j+1])
    return total_sum