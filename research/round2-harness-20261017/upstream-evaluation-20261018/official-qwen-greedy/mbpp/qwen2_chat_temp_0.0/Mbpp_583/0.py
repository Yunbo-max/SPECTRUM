def catalan_number(n):
    # Base case: the first Catalan number is 1
    if n == 0:
        return 1
    # Initialize the first two Catalan numbers
    catalan = [0] * (n + 1)
    catalan[0] = 1
    catalan[1] = 1
    # Calculate the Catalan numbers using the recurrence relation
    for i in range(2, n + 1):
        catalan[i] = 0
        for j in range(i):
            catalan[i] += catalan[j] * catalan[i - j - 1]
    return catalan[n]