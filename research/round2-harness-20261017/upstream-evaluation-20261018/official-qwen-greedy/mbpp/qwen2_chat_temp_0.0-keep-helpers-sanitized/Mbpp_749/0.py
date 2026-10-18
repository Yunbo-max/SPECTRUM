def sort_numeric_strings(arr):
    # Convert each string in the array to an integer
    arr = [int(i) for i in arr]
    # Sort the array in ascending order
    arr.sort()
    # Convert the sorted integers back to strings
    arr = [str(i) for i in arr]
    return arr