
sentence = input("Wpisz zdanie: ").strip().lower()



for i in sentence:

    if i not in "aeiouy": 
        
        continue
    
    if sentence.index(i) == 0:

        print(i.upper())
    
    else:
        print(i)
   
