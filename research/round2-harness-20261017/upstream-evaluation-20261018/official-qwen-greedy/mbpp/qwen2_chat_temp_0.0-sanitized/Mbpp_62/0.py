def smallest_num(lst):
    # Initialize the smallest number with the first element of the list
    smallest = lst[0]
    # Iterate through the list to find the smallest number
    for num in lst:
        if num < smallest:
            smallest = num
    # Return the smallest number found
    return smallest