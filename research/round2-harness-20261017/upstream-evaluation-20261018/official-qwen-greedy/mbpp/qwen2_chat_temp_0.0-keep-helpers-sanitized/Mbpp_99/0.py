def decimal_to_binary(decimal_number):
    # Convert the decimal number to binary using bin() function
    binary_number = bin(decimal_number)[2:]  # Remove the '0b' prefix
    return binary_number