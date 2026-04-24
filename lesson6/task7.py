def loguj(function):

    def wrap():

        print(f"Uruchamiam funkcję {function.__name__}.")
        
        function()
        
        print(f"Zakonczono funkcję {function.__name__}.")

    
    return wrap

@loguj

def numbers():

    for i in range(11):
        print(i)
    

numbers()