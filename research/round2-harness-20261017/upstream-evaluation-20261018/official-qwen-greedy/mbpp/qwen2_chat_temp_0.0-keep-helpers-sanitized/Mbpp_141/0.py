def pancake_sort(arr):
    n = len(arr)
    while n > 1:
        # Find the index of the maximum element in the unsorted part
        max_index = arr.index(max(arr[:n]))
        
        # Flip the array from the start to the index of the maximum element
        arr[:max_index+1] = arr[:max_index+1][::-1]
        
        # Flip the array from the start to the end of the unsorted part
        arr[:n] = arr[:n][::-1]
        
        # Decrease the size of the unsorted part
        n -= 1
    return arr