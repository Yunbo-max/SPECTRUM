def get_total_number_of_sequences(m, n):
    # Initialize a 2D list to store the number of sequences for each length and value
    dp = [[0 for _ in range(m + 1)] for _ in range(n + 1)]
    
    # Base case: There is one way to form a sequence of length 1 with any value
    for i in range(1, m + 1):
        dp[1][i] = 1
    
    # Fill the dp table
    for i in range(2, n + 1):
        for j in range(1, m + 1):
            # The number of sequences of length i with value j is the sum of sequences of length i-1 with values j/2, j/3, ..., j-1
            dp[i][j] = sum(dp[i - 1][k] for k in range(j // 2, j))
    
    # The total number of sequences of length n is the sum of sequences of length n with values 1, 2, ..., m
    return sum(dp[n][j] for j in range(1, m + 1))