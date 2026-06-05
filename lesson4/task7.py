sentence = input("Wpisz zdanie: ").strip().lower()



for i, ch in enumerate(sentence):

    if ch not in "aeiouy": 
        
        continue
    
    print(ch)
