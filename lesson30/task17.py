import asyncio
import time


async def pobierz_id_uzytkownika(nazwa_uzytkownika):
    await asyncio.sleep(1)
    return 42


async def pobierz_posty(id_uzytkownika):
    await asyncio.sleep(1)
    return [101, 102, 103]


async def pobierz_komentarze(id_postu):
    await asyncio.sleep(1)
    return [f"Komentarz do postu {id_postu}", "Drugi komentarz"]


async def main():
    start = time.perf_counter()
    nazwa_uzytkownika = "ania"

    id_uzytkownika = await pobierz_id_uzytkownika(nazwa_uzytkownika)
    id_postow = await pobierz_posty(id_uzytkownika)
    komentarze = await asyncio.gather(
        *(pobierz_komentarze(id_postu) for id_postu in id_postow)
    )

    print(f"ID użytkownika {nazwa_uzytkownika}: {id_uzytkownika}")
    print(f"Posty: {id_postow}")
    for id_postu, lista_komentarzy in zip(id_postow, komentarze):
        print(f"Komentarze do postu {id_postu}: {lista_komentarzy}")
    print(f"Czas wykonania: {time.perf_counter() - start:.2f} s")


if __name__ == "__main__":
    asyncio.run(main())
