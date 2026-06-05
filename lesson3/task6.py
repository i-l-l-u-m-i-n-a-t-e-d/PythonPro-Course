text = input("Wpisz dowolny ciąg znaków: ")

text_bool = bool(text)

print(f"Wartość logiczna tekstu: {text_bool}")

if text_bool:
    print("Tekst zawiera znaki.")
else:
    print("Nic nie wpisano.")
