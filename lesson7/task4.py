def oblicz_srednia(lista_ocen):
    
    assert len(lista_ocen) > 0, "Lista nie zawiera ocen."
    
    sum = 0.0
    for i in lista_ocen:
        sum += float(i)
    
    return sum/len(lista_ocen)


grades = [1,4,3,3.5,4.85,5.85]


r = oblicz_srednia(grades)

print(r)

