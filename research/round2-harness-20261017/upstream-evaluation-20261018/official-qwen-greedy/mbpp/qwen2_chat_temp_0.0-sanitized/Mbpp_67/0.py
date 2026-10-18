def bell_number(n):
    # Initialize the first few Bell numbers
    bell = [0] * (n + 1)
    bell[0] = 1
    for i in range(1, n + 1):
        bell[i] = sum(bell[j] * math.comb(i - 1, j) for j in range(i))
    return bell[n]