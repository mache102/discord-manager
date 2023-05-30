from datetime import timedelta

def add_one(string):

    digits = list(string)

    # Start from the rightmost digit and iterate backward
    carry = 1
    for i in range(len(digits)-1, -1, -1):
        digit = int(digits[i]) + carry

        # Update the current digit and check for carry
        digits[i] = str(digit % 10)
        carry = digit // 10

    # If there's a remaining carry, prepend it to the result
    if carry:
        digits.insert(0, str(carry))

    # Join the digits back into a string
    result = ''.join(digits)

    return result

def format_timedelta(timedelta_obj):
    # Extract the individual components from the timedelta object
    days = timedelta_obj.days
    hours = timedelta_obj.seconds // 3600
    minutes = (timedelta_obj.seconds % 3600) // 60
    seconds = timedelta_obj.seconds % 60

    # Create the formatted string
    formatted_str = f"{days}d {hours}h {minutes}m {seconds}s"

    return formatted_str
