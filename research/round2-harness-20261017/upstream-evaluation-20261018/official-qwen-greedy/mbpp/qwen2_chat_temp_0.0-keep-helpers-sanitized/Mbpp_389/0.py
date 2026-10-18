def find_lucas(n):
    # Base cases for the first two Lucas numbers
    if n == 0:
        return 2
    elif n == 1:
        return 1
    else:
        # Recursive call to find the n'th Lucas number
        return find_lucas(n-1) + find_lucas(n-2)