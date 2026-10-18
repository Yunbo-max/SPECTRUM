def check_monthnumber_number(month_number):
    # Check if the month number is between 1 and 12
    if 1 <= month_number <= 12:
        # Check if the month number is February
        if month_number == 2:
            return True
        # Check if the month number is April, June, September, or November
        elif month_number in [4, 6, 9, 11]:
            return True
        else:
            return False
    else:
        return False