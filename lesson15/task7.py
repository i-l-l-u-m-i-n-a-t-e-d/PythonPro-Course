def parse_url(url: str) -> dict:

    # https://api.example.com:8080/users/search?active=true

    # protocol - przed ://
    # domain - po :// do :
    # port - po : do /
    # path - od / do konca

    first = url.index("://")

    protocol = url[:first]

    rest = url[first + 3:]

    second = rest.index(":")

    domain = rest[:second]

    rest = rest[second + 1:]

    third = rest.index("/")

    port = rest[:third]

    path = rest[third:]

    result = {

        'protocol': protocol,
        'domain': domain,
        'port': port,
        'path': path

    }

    return result


url = "https://api.example.com:8080/users/search?active=true"

print(parse_url(url))