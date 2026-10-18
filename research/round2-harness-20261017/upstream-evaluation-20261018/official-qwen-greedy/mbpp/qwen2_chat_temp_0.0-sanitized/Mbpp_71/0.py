def comb_sort(arr):
    gap = len(arr)
    shrink_factor = 1.3
    while gap > 1 or any(arr[i] > arr[i + 1] for i in range(len(arr) - 1)):
        gap = int(gap / shrink_factor)
        for i in range(len(arr) - gap):
            if arr[i] > arr[i + gap]:
                arr[i], arr[i + gap] = arr[i + gap], arr[i]
    return arr