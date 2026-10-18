def validate(n):
    # Convert the integer to a string to easily iterate over each digit
    str_n = str(n)
    # Iterate over each digit in the string
    for digit in str_n:
        # Convert the digit back to an integer
        num = int(digit)
        # Check if the frequency of the digit is less than or equal to the digit itself
        if num > str_n.count(str(num)):
            return False
    return True