def find_solution(a, b, n):
    # Iterate through possible values of x
    for x in range(n // a + 1):
        # Calculate the corresponding y
        y = (n - a * x) // b
        # Check if y is an integer
        if y * b == n - a * x:
            return (x, y)
    # If no solution is found, return None
    return None