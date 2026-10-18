def even_position(lst):
    # Iterate through the list using a for loop
    for i in range(len(lst)):
        # Check if the index is even
        if i % 2 == 0:
            # Check if the number at the even index is even
            if lst[i] % 2 != 0:
                # If the number is odd, return False
                return False
    # If all even indices contain even numbers, return True
    return True