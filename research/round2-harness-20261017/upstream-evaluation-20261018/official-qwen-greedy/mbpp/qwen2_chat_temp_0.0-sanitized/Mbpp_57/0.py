def find_Max_Num(digits):
    # Sort the digits in descending order
    digits.sort(reverse=True)
    # Join the sorted digits to form the largest number
    largest_num = ''.join(map(str, digits))
    return int(largest_num)