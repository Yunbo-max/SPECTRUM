def lps(s):
    n = len(s)
    dp = [[0] * n for _ in range(n)]
    
    # Every single character is a palindrome of length 1
    for i in range(n):
        dp[i][i] = 1
    
    # Fill the table
    for length in range(2, n + 1):
        for start in range(n - length + 1):
            end = start + length - 1
            if s[start] == s[end]:
                dp[start][end] = dp[start + 1][end - 1] + 2
            else:
                dp[start][end] = max(dp[start + 1][end], dp[start][end - 1])
    
    return dp[0][n - 1]