def amicable_numbers_sum(n):
    def sum_of_divisors(num):
        """Calculate the sum of proper divisors of a number."""
        return sum([i for i in range(1, num) if num % i == 0])
    
    amicable_sum = 0
    for i in range(1, n + 1):
        if sum_of_divisors(i) == i:
            amicable_sum += i
    return amicable_sum