"""Korisničko uputstvo -> dokumentacija/AutoStakla_Korisnicko_uputstvo.docx (+ .pdf)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from docx_util import Doc, mark_update_fields, to_pdf  # noqa: E402

from autostakla import version  # noqa: E402

d = Doc("AutoStakla", "Uputstvo za korisnika", version.VERSION)
d.toc()

# ---------------------------------------------------------------- 1
d.h1("1. Šta je AutoStakla")
d.p("AutoStakla je program za vođenje lagera auto stakala. Umesto spiska na papiru, u programu se vidi ",
    ("koje staklo imate, koliko komada i gde tačno stoji", "b"), " – na kom skladištu, na kojoj polici i na kom mestu u nizu.")
d.bullets([
    [("Pretraga: ", "b"), "ukucate „golf 5“ i odmah vidite gde su sva takva stakla."],
    [("Ulaz i izlaz: ", "b"), "kad staklo stigne ili izađe, to se upiše jednim klikom."],
    [("Skladišta i police: ", "b"), "sami uređujete gde šta stoji."],
    [("Štampa: ", "b"), "spisak po skladištima, isti kao onaj koji ste do sada vodili na papiru."],
    [("Sigurnost: ", "b"), "program sam pravi rezervne kopije podataka i pamti svaku promenu."],
])
d.box("Važno:", "Program sve čuva sam – nema dugmeta „Sačuvaj“. Čim nešto upišete, upisano je.")

# ---------------------------------------------------------------- 2
d.h1("2. Instalacija")
d.p("Instalacija se radi samo jednom. Dobićete fajl ", ("AutoStakla_Setup_" + version.VERSION + ".exe", "b"), ".")
d.steps([
    "Dva puta kliknite na fajl AutoStakla_Setup.",
    ["Ako Windows prikaže plavi prozor „Windows protected your PC“, kliknite ", ("More info", "b"),
     ", pa ", ("Run anyway", "b"), ". To se pojavi samo prvi put – program je bezbedan."],
    ["Kliknite ", ("Dalje", "b"), ", pa ", ("Instaliraj", "b"), "."],
    ["Na kraju ostavite kvačicu „Pokreni AutoStakla“ i kliknite ", ("Završi", "b"), "."],
])
d.p("Posle instalacije na radnoj površini (desktopu) imate ikonicu ", ("AutoStakla", "b"),
    ". Program se uvek pokreće preko nje.")
d.box("Dobro je znati:", ["Sve je u jednom folderu: ", ("C:\\AutoStakla", "b"),
                          ". Ne treba instalirati ništa drugo (ni Python, ni bazu, ni PDF program)."])

# ---------------------------------------------------------------- 3
d.h1("3. Glavni ekran")
d.image("01_glavni_ekran_oznake", 16.5, "Glavni ekran – delovi su označeni brojevima")
d.table(["Br.", "Deo ekrana", "Čemu služi"], [
    ["1", "Pretraga", "Ovde kucate šta tražite – npr. golf 5, pezo 307, senzor."],
    ["2", "Filteri", "Suzite spisak: samo jedno skladište, jedna polica, samo sa senzorom, sa kamerom, polovna..."],
    ["3", "Tabela", "Spisak stakala: naziv, broj komada, skladište, polica, pozicija (redni broj), napomena."],
    ["4", "Dugmad za rad", "Ulaz, Izlaz, Premesti, Ispravi količinu, Pozicija / napomena."],
    ["5", "Ostala dugmad", "Izmena podataka o staklu i istorija promena."],
    ["6", "Meni", "Šifarnici (skladišta i police), Štampa, Prikaz (tema), Alati, Pomoć."],
], [1.2, 3.3, 12.0])
d.p("Na dnu ekrana piše koliko je mesta pronađeno i koliko je to ukupno komada. Skroz dole je verzija programa "
    "i kada je napravljena poslednja rezervna kopija.")
d.box("Savet:", "Za rad sa nekim staklom prvo kliknite na njegov red u tabeli – tada postaju dostupna dugmad Izlaz, "
                "Premesti i ostala.")

# ---------------------------------------------------------------- 4
d.h1("4. Kako da nađem staklo")
d.h2("4.1 Pretraga")
d.p("Kliknite u polje za pretragu i kucajte. Spisak se menja dok kucate – ne treba pritiskati Enter.")
d.image("02_pretraga_golf5", 16.5, "Pretraga „golf 5 senzor“ – odmah se vidi gde su sva takva stakla")
d.bullets([
    ["Nije bitno da li kucate velika ili mala slova, ni da li pišete kvačice (",
     ("skoda", "b"), " = ", ("škoda", "b"), ")."],
    ["Možete kucati više reči – prikazuju se stakla koja imaju ", ("sve", "b"), " te reči: ",
     ("golf 5 senzor", "b"), "."],
    ["Program zna različite načine pisanja marki: ", ("peugeot", "b"), " = ", ("pezo", "b"), ", ",
     ("renault", "b"), " = ", ("reno", "b"), ", ", ("volkswagen", "b"), " = ", ("vw", "b"), "."],
    ["Može se tražiti i po skladištu, polici ili napomeni: ", ("dvorište", "b"), ", ", ("garaža", "b"), ", ",
     ("krug", "b"), ", ", ("polovno", "b"), "."],
    ["„golf 5“ ne prikazuje Golf 4 sa godinom 05 – svaka reč mora biti početak neke reči u nazivu."],
])
d.p("Da obrišete pretragu, kliknite malo ", ("×", "b"), " na desnom kraju polja.")

d.h2("4.2 Filteri")
d.p("Ispod pretrage su padajuće liste. Sa njima se spisak sužava:")
d.table(["Filter", "Šta radi"], [
    ["Skladište", "Prikazuje samo jedno skladište (npr. Dvorište)."],
    ["Polica", "Kad je izabrano skladište – samo jedna njegova polica."],
    ["Tip", "Vetrobran, zadnje, bočno."],
    ["Senzor / Kamera / Polovno", "Da – samo ona koja imaju; Ne – samo ona koja nemaju; Svejedno – sva."],
    ["prikaži i ono čega nema", "Prikazuje i stakla kojih više nema na stanju (sivom bojom) – za istoriju."],
    ["Poništi filtere", "Vraća sve na početno i briše pretragu."],
], [4.5, 12.0])
d.image("03_filter_skladiste", 16.5, "Filter: skladište „Dvorište“, polica „I deo“ – kao stranica sa papira")

# ---------------------------------------------------------------- 5
d.h1("5. Pozicija – redni broj stakla")
d.p("Svako staklo ima ", ("poziciju", "b"), " – redni broj u skladištu, isto kao na papiru. Brojevi idu redom "
    "kroz celo skladište, preko svih polica (npr. na 1 Stalak: polica 1 ima brojeve 1–5, polica 2 brojeve 6–9...).")
d.bullets([
    ["Kad ubacite novo staklo između dva postojeća, ", ("svi ispod se sami pomere", "b"), "."],
    ["Svaki novi komad dobija ", ("svoj broj", "b"), ". Ako ubacite 2 komada, zauzimaju 2 broja."],
    ["Kad sa nekog mesta izađe poslednji komad, to mesto nestaje i svi ispod se pomere za jedan broj nagore."],
])
d.box("Primer:", ["Dvorište, I deo: Ducato je na 2, Audi A4 na 3. Ubacite ", ("2 komada", "b"),
                  " VW Touran na poziciju 3 → Touran je na 3 i 4, Audi A4 prelazi na 5, a sve ostalo ispod "
                  "se pomera za 2."])

# ---------------------------------------------------------------- 6
d.h1("6. Ulaz stakla")
d.p("Kad stigne novo staklo ili ga treba dodati na lager:")
d.steps([
    ["(Nije obavezno) U tabeli kliknite na staklo ", ("posle kog", "b"),
     " treba da stoji novo – program će ponuditi poziciju odmah ispod njega."],
    ["Kliknite dugme ", ("＋ Ulaz", "b"), "."],
    ["Kod „Staklo“ počnite da kucate naziv i izaberite ga sa liste. Ako takvog stakla još nema u programu, "
     "kliknite ", ("Novo staklo…", "b"), " (poglavlje 7)."],
    "Izaberite skladište i policu.",
    "Proverite poziciju. Pored nje piše koji su brojevi na toj polici; najveći broj znači „na kraj police“.",
    "Upišite količinu i, ako želite, napomenu.",
    ["Kliknite ", ("Upiši ulaz", "b"), "."],
])
d.image("04_ulaz", 12.5, "Ulaz: 2 komada na poziciju 3 – program ispod ispisuje šta će se desiti")

# ---------------------------------------------------------------- 7
d.h1("7. Novo staklo i izmena stakla")
d.p("Staklo se jednom unese u program, a posle se samo bira sa liste. Prozor se otvara preko ",
    ("Novo staklo…", "b"), " u Ulazu, ili dugmetom ", ("Izmeni staklo…", "b"), " za izabrani red.")
d.image("05_novo_staklo", 12.0, "Podaci o staklu")
d.table(["Polje", "Šta upisati"], [
    ["Naziv", "Kako ga vi zovete, npr. „VW Golf 5 i 6 SENZOR“. Po ovome se najviše pretražuje."],
    ["Tip stakla", "Vetrobran, zadnje, bočno ili ostalo."],
    ["Senzor", "Kvačica ako ima senzor; pored može oblik (romb, krug, kruška, kocka...)."],
    ["Kamera", "Kvačica ako ima kameru; pored može opis (uska, široka...)."],
    ["Pločica retrovizora", "Trougao (stari tip), okrugla, niža, viša, bez pločice..."],
    ["Polovno staklo", "Kvačica ako je polovno."],
    ["Napomena", "Bilo šta važno o samom staklu."],
    ["Vozila", "Nije obavezno: za koja vozila odgovara (marka, model, godine)."],
], [4.0, 12.5])
d.box("Pažnja:", "Izmena stakla menja podatke na SVIM mestima gde to staklo stoji. "
                 "Ako treba nešto samo za jedno mesto, koristite „Pozicija / napomena…“.")

# ---------------------------------------------------------------- 8
d.h1("8. Izlaz stakla")
d.steps([
    "U tabeli kliknite na staklo koje izlazi (prodato, ugrađeno...).",
    ["Kliknite ", ("− Izlaz", "b"), "."],
    "Upišite koliko komada izlazi (obično 1) i, ako želite, napomenu (npr. kome je ugrađeno).",
    ["Kliknite ", ("Upiši izlaz", "b"), "."],
])
d.image("06_izlaz", 9.5, "Izlaz stakla")
d.p("Ne može izaći više komada nego što ih ima na stanju – program to ne dozvoljava.")

# ---------------------------------------------------------------- 9
d.h1("9. Ispravka količine")
d.p("Kad prebrojite stakla i broj u programu nije tačan, izaberite red, kliknite ", ("✎ Ispravi količinu", "b"),
    ", upišite tačnu količinu i razlog. Program sam izračuna razliku i zapamti je u istoriji.")
d.image("07_ispravka", 9.5, "Ispravka količine")

# ---------------------------------------------------------------- 10
d.h1("10. Premeštanje")
d.p("Kad staklo prenesete na drugo mesto (drugo skladište, drugu policu):")
d.steps([
    ["Izaberite red i kliknite ", ("⇄ Premesti", "b"), "."],
    "Upišite koliko komada se premešta.",
    "Izaberite novo skladište, policu i poziciju.",
    ["Kliknite ", ("Premesti", "b"), ". Brojevi na starom i novom mestu se sami srede."],
])
d.image("08_premesti", 11.0, "Premeštanje na drugo mesto")

# ---------------------------------------------------------------- 11
d.h1("11. Pozicija i napomena")
d.p("Dugme ", ("Pozicija / napomena…", "b"), " služi da:")
d.bullets([
    "promenite napomenu za to mesto (npr. „H137 163“, „oštećen ugao“, „rezervisano za Marka“);",
    "pomerite staklo na drugu poziciju ili drugu policu u istom skladištu – ostala stakla se sama prenumerišu.",
])
d.image("09_pozicija_napomena", 11.0, "Izmena pozicije i napomene")

# ---------------------------------------------------------------- 12
d.h1("12. Istorija")
d.p("Izaberite red i kliknite ", ("Istorija", "b"), " (ili dva puta kliknite na red). Vidi se svaki ulaz, izlaz, "
    "ispravka i premeštanje za to mesto, sa datumom, količinom i napomenom.")
d.image("10_istorija", 12.5, "Istorija promena za jedno mesto")

# ---------------------------------------------------------------- 13
d.h1("13. Skladišta i police")
d.p("Meni ", ("Šifarnici → Skladišta i police…", "b"), ". Levo su skladišta, desno police izabranog skladišta.")
d.image("11_skladista_police", 15.5, "Skladišta i police")
d.table(["Dugme", "Šta radi"], [
    ["Dodaj…", "Novo skladište (dobija odmah „Polica 1“) ili nova polica. Upisujete naziv i opis."],
    ["Izmeni…", "Promena naziva i opisa (može i dupli klik na naziv)."],
    ["Obriši", "Brisanje. Ne može dok na njemu ima stakala – prvo ih premestite ili razdužite."],
    ["▲ Gore / ▼ Dole", "Redosled – kako se prikazuju u programu i na štampi."],
], [3.8, 12.7])
d.image("12_novo_skladiste", 8.5, "Naziv i opis skladišta")
d.box("Dobro je znati:", "Prazno skladište koje je ranije imalo stakla ne briše se zauvek – samo se skloni iz rada, "
                         "da istorija ostane sačuvana.")

# ---------------------------------------------------------------- 14
d.h1("14. Štampa")
d.p("Program pravi PDF fajl koji se odmah otvara u internet pregledaču (Edge ili Chrome). Odatle se štampa "
    "uobičajeno: ", ("Ctrl + P", "b"), " ili ikonica štampača.")
d.h2("14.1 Spisak po skladištima")
d.steps([
    ["Meni ", ("Štampa → Spisak po skladištima (PDF)…", "b"), " (ili ", ("Ctrl + P", "b"), ")."],
    "Označite koja skladišta želite (podrazumevano su sva).",
    "Ostavite kvačicu „svako skladište na novoj strani“ ako želite da se lako razdvoje.",
    ["Kliknite ", ("Napravi PDF", "b"), "."],
])
d.image("13_stampa_izbor", 6.5, "Izbor skladišta za štampu")
d.image("18_pdf_spisak", 10.0, "Izgled odštampanog spiska – kao na papiru, police su odvojene linijom")
d.h2("14.2 Trenutni prikaz")
d.p("Meni ", ("Štampa → Trenutni prikaz (PDF)", "b"), " štampa tačno ono što je trenutno u tabeli – npr. rezultat "
    "pretrage „senzor“ ili samo jedno skladište.")
d.p("Odštampani PDF fajlovi ostaju sačuvani u folderu ", ("C:\\AutoStakla\\stampa", "b"), ".")

# ---------------------------------------------------------------- 15
d.h1("15. Svetla i tamna tema")
d.p("Meni ", ("Prikaz", "b"), " → ", ("Svetla tema", "b"), " ili ", ("Tamna tema", "b"),
    ". Program pamti izbor i sledeći put se otvara u istoj temi.")
d.image("19_meni_prikaz", 3.5)
d.image("20_glavni_tamna", 15.5, "Tamna tema")

# ---------------------------------------------------------------- 16
d.h1("16. Alati: rezervne kopije, provera, ažuriranje")
d.image("14_meni_alati", 5.0, "Meni Alati")
d.h2("16.1 Rezervne kopije (backup)")
d.p("Program ", ("sam", "b"), " pravi kopiju podataka svaki put kad se zatvori, pre svakog ažuriranja i pre svake "
    "promene baze. Čuva se poslednjih 30 kopija u folderu ", ("C:\\AutoStakla\\backup", "b"), ".")
d.bullets([
    [("Napravi backup sada", "b"), " – odmah pravi kopiju (npr. pre većih izmena)."],
    [("Otvori folder sa backup-ima", "b"), " – otvara folder sa kopijama."],
])
d.box("Preporuka:", "Povremeno (npr. jednom nedeljno) prekopirajte folder C:\\AutoStakla\\backup na USB ili "
                    "OneDrive. Ako se laptop pokvari, podaci ostaju sačuvani.")
d.h2("16.2 Provera baze")
d.p(("Alati → Provera baze…", "b"), " pokazuje verziju programa i baze i proverava da li su podaci ispravni. "
    "Ako piše „Sve je u redu“, nema šta da se radi.")
d.image("17_provera_baze", 9.5, "Provera baze")
d.h2("16.3 Ažuriranje programa")
d.p("Kad dobijete novu verziju (fajl ", ("AutoStakla_update_….zip", "b"), ", npr. preko Vibera ili linka):")
d.steps([
    "Sačuvajte zip fajl (npr. u Preuzimanja / Downloads). Ne raspakujte ga.",
    ["Dva puta kliknite na zip – otvoriće se kao folder. Unutra pročitajte ", ("OBAVEZNO_PROCITAJ.txt", "b"),
     " (šta je novo) i, ako želite, novo uputstvo."],
    ["U programu: meni ", ("Alati → Ažuriraj iz fajla…", "b"), " i izaberite taj isti zip."],
    ["Program pokaže trenutnu i novu verziju – kliknite ", ("Yes / Da", "b"), "."],
    "Program napravi backup, zatvori se, zameni verziju i sam se ponovo otvori, pa prikaže šta je novo.",
])
d.p("Podaci se pri ažuriranju ne diraju. Ako bilo šta krene naopako, vraća se prethodna verzija.")
d.box("Uz svaku verziju:", "stiže i novo korisničko uputstvo. Ono je i u samom programu – vidi poglavlje 17.")
d.h2("16.4 Dijagnostika – kad nešto ne radi")
d.p("Ako se pojavi greška ili program radi čudno: ", ("Alati → Napravi dijagnostiku…", "b"),
    ". Na desktopu se pojavi fajl ", ("AutoStakla_dijagnostika_….zip", "b"),
    " – pošaljite ga Milošu. Na pitanje „staviti i kopiju baze?“ odgovorite Da ako problem ima veze sa podacima.")

# ---------------------------------------------------------------- 17
d.h1("17. Pomoć: uputstvo i šta je novo")
d.p("Meni ", ("Pomoć", "b"), ":")
d.bullets([
    [("Korisničko uputstvo (PDF)", "b"), " – otvara ovo uputstvo (ili taster ", ("F1", "b"),
     "). Uvek je ono koje odgovara vašoj verziji programa."],
    [("Šta je novo u ovoj verziji", "b"), " – šta je dodato, izmenjeno ili uklonjeno. Prikazuje se i samo, "
                                          "odmah posle ažuriranja."],
    [("O programu", "b"), " – verzija i folder programa."],
])

# ---------------------------------------------------------------- 18
d.h1("18. Česta pitanja")
d.table(["Pitanje", "Odgovor"], [
    ["Gde se čuvaju podaci?", "U C:\\AutoStakla\\data. Ne brišite i ne premeštajte taj folder."],
    ["Moram li da čuvam?", "Ne. Sve se upisuje odmah."],
    ["Obrisao sam / izdao pogrešno staklo.", "Uradite Ispravku količine ili Ulaz – istorija pamti obe radnje."],
    ["Dugmad Izlaz, Premesti... su siva.", "Prvo kliknite na red u tabeli."],
    ["Ne vidim staklo koje znam da postoji.", "Kliknite „Poništi filtere“ – možda je uključen neki filter."],
    ["Piše „Program je već pokrenut“.", "Program je već otvoren – pogledajte dole na traci zadataka."],
    ["PDF se ne otvara.", "Fajl je u C:\\AutoStakla\\stampa – prevucite ga u Edge ili Chrome."],
    ["Pojavila se poruka o grešci.", "Napravite dijagnostiku (16.4) i pošaljite je Milošu."],
], [5.5, 11.0])

# ---------------------------------------------------------------- 19
d.h1("19. Brzi pregled")
d.table(["Želim da...", "Uradite ovo"], [
    ["nađem staklo", "Kucajte u pretragu (npr. golf 5 senzor)"],
    ["upišem novo staklo na lager", "＋ Ulaz → Novo staklo… → mesto → količina → Upiši ulaz"],
    ["upišem da je staklo izašlo", "Klik na red → − Izlaz → Upiši izlaz"],
    ["ispravim broj komada", "Klik na red → ✎ Ispravi količinu"],
    ["prenesem staklo na drugo mesto", "Klik na red → ⇄ Premesti"],
    ["promenim poziciju ili napomenu", "Klik na red → Pozicija / napomena…"],
    ["vidim šta se dešavalo sa staklom", "Dupli klik na red (Istorija)"],
    ["dodam ili preimenujem skladište/policu", "Šifarnici → Skladišta i police…"],
    ["odštampam spisak", "Štampa → Spisak po skladištima (Ctrl + P)"],
    ["promenim temu", "Prikaz → Svetla / Tamna tema"],
    ["ažuriram program", "Alati → Ažuriraj iz fajla…"],
    ["otvorim uputstvo / vidim šta je novo", "Pomoć → Korisničko uputstvo (F1) / Šta je novo"],
    ["prijavim problem", "Alati → Napravi dijagnostiku… → pošaljem zip Milošu"],
], [6.5, 10.0])

path = d.save("AutoStakla_Korisnicko_uputstvo")
print(path)
print(to_pdf(path))
mark_update_fields(path)
