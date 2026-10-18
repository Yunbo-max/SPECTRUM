def last_Digit_Factorial(n):
    # Initialize the result to 1 (since 1! = 1)
    result = 1
    
    # Loop from 2 to n
    for i in range(2, n + 1):
        # Multiply the result by the current number
        result *= i
    
    # Return the last digit of the result
    return result % 10