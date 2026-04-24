def powtorz(n):
    def decorator(func):
        def wrap():

            for i in range(n):

                func()
            
        
        return wrap
        
    return decorator

i = 1

@powtorz(5)
def cycle():

    global i

    print(f"{i} wyswietlenie.")
    
    i += 1
    

    
cycle()