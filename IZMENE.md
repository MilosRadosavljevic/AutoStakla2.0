# AutoStakla – izmene po verzijama

Odavde se pravi OBAVEZNO_PROCITAJ.txt koji ide korisniku uz svaku verziju.
Build NEĆE proći ako za trenutnu verziju (src\autostakla\version.py) ovde nema odeljka.

Format (pisati za korisnika, jednostavno):

    ## x.y.z (dd.mm.yyyy)
    ### Dodato
    - ...
    ### Izmenjeno
    - ...
    ### Ispravljeno
    - ...
    ### Uklonjeno
    - ...

Podnaslovi koji nemaju stavke se izostave. Najnovija verzija ide na vrh.

---

## 2.0.0 (10.11.2026)
### Dodato
- AutoStaklaBetter: novi meni „Poslovanje“ (samo u Better izdanju; osnovna verzija ostaje 1.x).
- Izlaz sa razlogom: prodato, razbijeno, vraćeno dobavljaču, zamena po reklamaciji, ostalo.
- Prodaja: cena po komadu (sa PDV-om), kupac, vozilo, tablice, ugradnja; prozor „Prodaja“ sa pretragom po periodu.
- Kupci: ime, telefon, napomena – izbor pri prodaji i predračunu.
- Ulaz sa razlogom: nabavka, vraćeno od kupca, ostalo; za nabavku dobavljač, nabavna cena (bez PDV-a) i broj dokumenta.
- Dobavljači i cene stakla po dobavljačima, sa istorijom cena; pri ulazu se predlaže cena iz cenovnika.
- Analitika: promet, zarada i marža uz poređenje sa prethodnim periodom, prodaja po mesecima (grafikon),
  najprodavanija stakla, najčešća vozila, stakla koja stoje, predlog nabavke sa najjeftinijim dobavljačem,
  reklamacije po dobavljaču; izvoz u Excel i PDF.
- Reklamacije: prijava iz prodaje, statusi (prijavljena, kod dobavljača, odobrena, odbijena, rešena), ishod i trošak.
- Predračun i otpremnica u PDF (nisu fiskalni računi); podaci o firmi i PDV stopa.
- Vozila iz naziva stakla: program predloži marku, model i godine, a vi potvrdite.
### Izmenjeno
- Istorija mesta prikazuje i razlog, cenu, kupca i dobavljača.

## 1.0.0 (07.11.2026)
### Dodato
- Prva verzija programa AutoStakla.
- Ceo spisak sa papira je već unet: 11 skladišta, 329 mesta, 390 komada stakla.
- Pretraga: ukucate npr. „golf 5 senzor“ i odmah vidite gde stoji svako takvo staklo.
- Filteri: skladište, polica, tip stakla, senzor, kamera, polovno.
- Ulaz, izlaz, ispravka količine i premeštanje stakala; za svako mesto se vidi istorija.
- Pozicija (redni broj) na polici: kad ubacite staklo između dva, ostala se sama pomere.
- Napomena za svako mesto (dugme „Pozicija / napomena…“).
- Skladišta i police: dodavanje, izmena naziva i opisa, brisanje, redosled.
- Štampa u PDF: spisak po skladištima (kao na papiru) i štampa trenutnog prikaza.
- Svetla i tamna tema (meni Prikaz) – program pamti izbor.
- Automatske rezervne kopije podataka, provera baze, ažuriranje iz fajla, dijagnostika.
- Meni Pomoć: korisničko uputstvo i „Šta je novo“.
