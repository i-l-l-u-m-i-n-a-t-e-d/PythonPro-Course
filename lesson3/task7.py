try:
    word = int("Python")
except ValueError:
    print("Wystąpił błąd ValueError.")
    print("Nie można zamienić tekstu 'Python' na liczbę całkowitą.")

# word = int("Python")

# ta linia nie dzialala, bo "Python" sklada się z liter
# funkcja int() może zamienic na liczbę tylko tekst zapisany jako liczba np. "123"
