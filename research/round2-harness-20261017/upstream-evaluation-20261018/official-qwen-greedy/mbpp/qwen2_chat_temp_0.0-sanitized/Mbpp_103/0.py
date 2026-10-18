def eulerian_num(n, m):
    # Base cases
    if m > n or m < 0:
        return 0
    if m == 0:
        return 1
    if m == 1:
        return n
    # Recursive case
    return (n - m) * eulerian_num(n - 1, m - 1) + m * eulerian_num(n - 1, m)