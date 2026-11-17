# Kolorowanka po numerach (iPad + Apple Pencil)

Cała aplikacja to folder **`app`**. Działa w Safari na iPadzie, a po dodaniu do ekranu
początkowego otwiera się jak zwykła aplikacja: z własną ikoną, na pełnym ekranie i bez internetu.

Oprócz gotowych obrazków możesz **wgrać własne zdjęcia**: aplikacja sama przerobi je
na kolorowankę po numerach (kontury, pola i numery), bez internetu i bez wysyłania zdjęcia
gdziekolwiek. Szczegóły w sekcji [Własne zdjęcia jako kolorowanki](#własne-zdjęcia-jako-kolorowanki).

W środku jest 10 gotowych obrazków (każdy ma 870–1610 pól):

| Kategoria  | Obrazki |
|------------|---------|
| Mandale    | Mandala lotosu, Gwiezdna mandala, Witrażowa rozeta, Mandala ogrodowa (najtrudniejsza) |
| Krajobrazy | Zachód słońca nad jeziorem, Zamek z bajki, Balony nad doliną |
| Zwierzęta  | Podwodny świat, Motyl w ogrodzie, Sowa w blasku księżyca |

---

## Instalacja na iPadzie (na stałe, zalecana)

Aplikację trzeba raz wrzucić do internetu, żeby iPad mógł ją pobrać. Najprościej zrobić to
w darmowym serwisie **Netlify**: przeciągasz folder i to wszystko.

**Na Macu:**

1. Otwórz w przeglądarce stronę **https://app.netlify.com/drop**.
2. Załóż darmowe konto albo się zaloguj (np. przez Google lub e-mail).
3. W Finderze otwórz folder `claude_projects` → `kolorowanka`. Przeciągnij folder **`app`**
   na pole do upuszczania plików na stronie Netlify.
4. Po kilku sekundach dostaniesz adres w rodzaju `https://cos-tam-123abc.netlify.app`.
   Możesz go zmienić na łatwiejszy: **Site configuration → Change site name**
   (np. `kolorowanka-moja`, wtedy adres to `https://kolorowanka-moja.netlify.app`).

**Na iPadzie:**

5. Otwórz ten adres w **Safari**.
6. Stuknij przycisk **Udostępnij** (kwadrat ze strzałką w górę), a potem
   **„Do ekranu początkowego”**. Jeśli pojawi się przełącznik **„Otwórz jako aplikację internetową”**,
   zostaw go włączonego. Na koniec stuknij **Dodaj**.
7. Od teraz uruchamiaj Kolorowankę ikoną z ekranu początkowego. Za pierwszym razem iPad
   musi mieć internet, żeby pobrać obrazki (około 5 MB). Później działa też offline.

Postępy w malowaniu zapisują się na iPadzie, w samej aplikacji. Nie usuwaj danych tej strony
w Ustawieniach Safari, bo stracisz pokolorowane obrazki.

---

## Szybki test bez zakładania konta (iPad i Mac w tej samej sieci Wi-Fi)

1. Na Macu otwórz **Terminal** i wpisz:
   ```bash
   cd ~/claude_projects/kolorowanka/app && python3 -m http.server 8000
   ```
2. Na iPadzie otwórz w Safari adres **`http://192.168.1.146:8000`**.
   To adres Maca w sieci domowej i może się zmienić. Aktualny sprawdzisz w Ustawieniach systemowych
   → Wi-Fi → Szczegóły → Adres IP.
3. Tak to działa tylko wtedy, gdy Mac jest włączony, a polecenie w Terminalu pracuje.
   Kreski namalowane w trybie testowym nie przejdą do wersji z Netlify.

---

## Własne zdjęcia jako kolorowanki

1. W galerii, w sekcji **Twoje zdjęcia**, stuknij kafelek **Dodaj zdjęcie** i wybierz zdjęcie
   z galerii iPada albo zrób nowe.
2. Wybierz **liczbę kolorów** (12–30) i **szczegóły**:
   - **Mało**: tylko plamy koloru ze zdjęcia, mniej i większe pola,
   - **Średnio / Dużo / Bardzo dużo**: duże plamy są dodatkowo dzielone na kawałki jak w witrażu.
     Pól jest coraz więcej (orientacyjnie ok. 1500 / 3000 / 5500 przy wyraźnym zdjęciu).
3. Stuknij podgląd, żeby zobaczyć kontury z numerami. Stuknij jeszcze raz, żeby wrócić do kolorów.
4. Wpisz nazwę i stuknij **Dodaj i maluj**.

Przerabianie przy „Bardzo dużo” może potrwać nawet ok. minuty. Zdjęcie jest przerabiane na iPadzie, bez internetu, i nigdzie nie jest wysyłane. Gotowa kolorowanka
zostaje tylko w aplikacji na tym iPadzie. Przycisk **Usuń** na kafelku kasuje ją z galerii, ale nie
rusza oryginalnego zdjęcia w Zdjęciach. Najlepiej wychodzą zdjęcia z wyraźnym tematem:
zwierzęta, kwiaty, krajobrazy, portrety.

## Jak malować

- **Wybór obrazka:** po otwarciu aplikacji widzisz galerię. Stuknij obrazek i możesz malować.
- **Kolor:** wybierasz go z paska na dole. Numer na kółku odpowiada numerom w polach.
  Pola z wybranym numerem są lekko podświetlone, więc łatwo je znaleźć.
- **Rysik:** maluje naprawdę, kreska po kresce. Mocniejszy nacisk daje trochę grubszą kreskę.
- **Grubość pędzla:** suwak w prawym dolnym rogu.
- **Palce:** dwoma palcami przybliżasz, oddalasz i przesuwasz obrazek. Po pierwszym użyciu rysika
  przesuwać można też jednym palcem, a dłoń oparta o ekran nie maluje.
- **Stuknięcie dwoma palcami** albo przycisk **Cofnij** cofa ostatnią kreskę.
- **W polu** (włączone na start): kolor nie wychodzi poza pole, w którym zaczniesz kreskę,
  nawet jeśli rysik zjedzie za linię. Po wyłączeniu malujesz zupełnie swobodnie.
- **Gumka:** ściera namalowany kolor.
- **✓ przy kolorze** oznacza, że wszystkie pola z tym numerem są już pomalowane.
- **Podgląd:** pokazuje, jak wygląda gotowy obrazek.
- **Zapisz:** otwiera menu udostępniania, w którym wybierasz „Zapisz obraz”, żeby obrazek trafił do Zdjęć.
- **Od nowa** (na kafelku w galerii): czyści obrazek.

---

## Dla ciekawskich: skąd się biorą obrazki

Obrazki generują skrypty w folderze `tools` (Python z bibliotekami numpy, scipy, scikit-image
i pillow). Każdy obrazek powstaje z kształtów, które skrypt dzieli na pola, a potem dobiera
miejsce i wielkość numeru w każdym polu. Kolejny obrazek dodaje się nową funkcją w `tools/scenes.py`
albo `tools/mandalas.py`, wpisem w `PICTURES` i poleceniem `python build.py <id>`. Po każdej zmianie
w folderze `app` podbij numer `VERSION` w `app/sw.js` i przeciągnij folder `app` na Netlify jeszcze raz
(w zakładce **Deploys** swojej strony).
