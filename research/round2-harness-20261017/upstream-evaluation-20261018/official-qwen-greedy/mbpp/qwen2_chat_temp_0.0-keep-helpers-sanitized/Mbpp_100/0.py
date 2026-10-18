def next_smallest_palindrome(n):
    # Convert the number to a string to easily manipulate its digits
    num_str = str(n)
    # Find the length of the number
    length = len(num_str)
    # Check if the number is a palindrome
    if num_str == num_str[::-1]:
        # If it is, find the next palindrome by incrementing the last digit
        for i in range(length - 1, -1, -1):
            if num_str[i] != '9':
                num_str[i] = str(int(num_str[i]) + 1)
                break
        else:
            # If all digits are 9, increment the first digit and set all others to 0
            num_str = '1' + '0' * (length - 1)
    else:
        # If it's not a palindrome, find the next palindrome by incrementing the last digit
        for i in range(length - 1, -1, -1):
            if num_str[i] != '9':
                num_str[i] = str(int(num_str[i]) + 1)
                break
        else:
            # If all digits are 9, increment the first digit and set all others to 0
            num_str = '1' + '0' * (length - 1)
    # Convert the string back to an integer and return it
    return int(num_str)