liczba_str = "5.8"

liczba_float = float(liczba_str)
liczba_int = int(liczba_float)

print("Po konwersji na float:", liczba_float)
print("Po konwersji na int:", liczba_int)

# Podczas konwersji float na int część dziesiętna zostaje obcięta.
# Liczba 5.8 nie została zaokrąglona do 6, tylko obcięta do 5.
