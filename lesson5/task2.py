def description_of_book(title: str, author: str, year_of_release: int = 2024):

    return f"Książka {title.title()} została napisana przez {author.title()} i wydana w roku {year_of_release}."

print(description_of_book("quo vadis", "henryk Sienkiewicz"))

print(description_of_book(title="Chlopi", author="Władysław reymont", year_of_release=1904))