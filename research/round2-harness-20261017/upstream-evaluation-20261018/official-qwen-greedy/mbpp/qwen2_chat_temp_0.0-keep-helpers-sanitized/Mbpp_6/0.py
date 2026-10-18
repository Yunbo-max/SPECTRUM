def differ_At_One_Bit_Pos(num1, num2):
    # XOR the two numbers
    xor_result = num1 ^ num2
    # Count the number of set bits in the XOR result
    count = bin(xor_result).count('1')
    # If the count is 1, the numbers differ at one bit position
    return count == 1