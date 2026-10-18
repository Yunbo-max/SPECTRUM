def is_Diff(n):
    # Calculate the difference between the sum of digits at odd positions and the sum of digits at even positions
    odd_sum = sum(int(digit) for i, digit in enumerate(str(n)) if i % 2 != 0)
    even_sum = sum(int(digit) for i, digit in enumerate(str(n)) if i % 2 == 0)
    
    # Check if the difference is divisible by 11
    return odd_sum - even_sum % 11 == 0