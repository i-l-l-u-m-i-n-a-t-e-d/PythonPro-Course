from faker import Faker


fake = Faker("pl_PL")

print("10 losowych polskich imion i nazwisk:")
for number in range(1, 11):
    print(f"{number}. {fake.name()}")

print()
print("10 losowych zdań:")
for number in range(1, 11):
    print(f"{number}. {fake.sentence(nb_words=10)}")


# Uruchomienie:
# python faker_test.py
