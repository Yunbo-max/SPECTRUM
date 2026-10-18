def first_Digit(n):
    """
    This function takes an integer n as input and returns the first digit of n.
    """
    # Convert the number to a string to easily access the first character
    num_str = str(n)
    # Return the first character of the string, which is the first digit
    return int(num_str[0])