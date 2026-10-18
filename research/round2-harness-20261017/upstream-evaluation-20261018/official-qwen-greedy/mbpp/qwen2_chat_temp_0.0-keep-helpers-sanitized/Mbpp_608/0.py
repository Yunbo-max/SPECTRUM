def bell_Number(n):
    # Initialize the first bell number
    bell = [0] * (n + 1)
    bell[0] = 1
    
    # Calculate the bell numbers using the recursive formula
    for i in range(1, n + 1):
        bell[i] = sum(bell[j] * math.factorial(i - j) for j in range(i))
    
    return bell[n]