# PUT - caly zasob
put_body = {
    "name": "Kasia",
    "email": "k.nowak@example.com",
    "city": "Warszawa"
}

# PATCH - tylko zmiana
patch_body = {
    "name": "Kasia"
}

# PATCH jest bardziej oszczedny, bo wysyla tylko pole name.
# PUT wysyla caly obiekt i zwykle zastepuje caly zasob.