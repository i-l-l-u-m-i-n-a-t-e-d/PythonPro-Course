def calculate_avg(*args):

    sum = 0.0
    it = 0

    for i in args:

        if type(i) is int or type(i) is float:

            sum += i
            it += 1


    if it != 0:

        return sum/it
    
    else:

        return 0
    

result = calculate_avg(1, 4.234, 123.09, "siema", 12.90, "txt")

print(f"{result:.4f}")
