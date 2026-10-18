def reverse_Array_Upto_K(arr, k):
    # Reverse the array from the start to the given position k
    arr[:k] = arr[:k][::-1]
    return arr