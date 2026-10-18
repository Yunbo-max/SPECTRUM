def sum_average(n):
    # Calculate the sum of first n natural numbers
    sum_n = n * (n + 1) // 2
    # Calculate the average of first n natural numbers
    average_n = sum_n / n
    return sum_n, average_n