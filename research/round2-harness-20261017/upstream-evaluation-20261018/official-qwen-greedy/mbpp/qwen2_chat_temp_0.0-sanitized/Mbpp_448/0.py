def cal_sum(n):
    # Initialize the first three Perrin numbers
    p1, p2, p3 = 3, 0, 2
    # Initialize the sum
    sum_perrin = 0
    # Calculate the sum of the first n Perrin numbers
    for _ in range(n):
        sum_perrin += p1
        # Update the next Perrin number
        p1, p2, p3 = p2, p3, p1 + p2 + p3
    return sum_perrin