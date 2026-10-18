def dog_age(human_years):
    # Calculate the dog's age in dog's years
    if human_years <= 2:
        return human_years * 10.5
    else:
        return 21 + (human_years - 2) * 4