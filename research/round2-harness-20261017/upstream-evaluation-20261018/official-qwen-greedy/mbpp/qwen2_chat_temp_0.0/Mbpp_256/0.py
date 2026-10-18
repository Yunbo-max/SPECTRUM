def count_Primes_nums(n):
    # Initialize a list to keep track of prime numbers
    primes = [True] * (n + 1)
    primes[0] = primes[1] = False  # 0 and 1 are not prime numbers
    
    # Iterate through numbers starting from 2
    for i in range(2, int(n**0.5) + 1):
        if primes[i]:
            # Mark all multiples of i as non-prime
            for j in range(i*i, n + 1, i):
                primes[j] = False
    
    # Count the number of prime numbers
    return sum(primes)