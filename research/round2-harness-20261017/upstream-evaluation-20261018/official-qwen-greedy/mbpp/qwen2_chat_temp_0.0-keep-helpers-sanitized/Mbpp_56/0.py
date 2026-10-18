def check(n):
    # Reverse the number
    reversed_n = int(str(n)[::-1])
    # Check if the number is one less than twice its reverse
    return n == 2 * reversed_n - 1