def rotate_right(lst, n):
    # Calculate the effective rotation needed
    n = n % len(lst)
    # Perform the rotation
    rotated_list = lst[-n:] + lst[:-n]
    return rotated_list