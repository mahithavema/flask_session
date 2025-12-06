import random

def generate_otp():
    otp = str(random.randint(100000, 999999))
    return otp
