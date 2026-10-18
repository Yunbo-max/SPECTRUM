def shell_sort(arr):
    n = len(arr)
    # Start with a big gap and reduce it
    gap = n // 2
    while gap > 0:
        # Do a gapped insertion sort for this gap size.
        for i in range(gap, n):
            temp = arr[i]
            # Shift earlier gap-sorted elements up until the correct location for arr[i] is found
            j = i
            while j >= gap and arr[j - gap] > temp:
                arr[j] = arr[j - gap]
                j -= gap
            # Put temp (the original arr[i]) in its correct location
            arr[j] = temp
        # Reduce the gap
        gap //= 2
    return arr