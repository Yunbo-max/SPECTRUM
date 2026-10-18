def odd_position(lst):
    # Iterate through the list starting from the first odd index
    for i in range(1, len(lst), 2):
        # Check if the number at the current odd index is even
        if lst[i] % 2 == 0:
            return False
    return True