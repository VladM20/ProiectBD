# Aplicație pentru Gestionarea unui Cabinet de Medicină de Familie

Acest proiect reprezintă o soluție software dezvoltată pentru gestionarea completă a fluxului de lucru dintr-un cabinet de medicină de familie. Aplicația este scrisă în limbajul de programare Python și utilizează biblioteca Streamlit pentru a oferi o interfață grafică interactivă. Datele sunt gestionate printr-o bază de date relațională SQL Server, conexiunea fiind realizată prin intermediul driverului ODBC.

### Funcționalități Principale
Platforma este structurată în cinci secțiuni esențiale: Dashboard, Orar Medici, Dosar Pacient, Gestiune Pacienți și Gestiune Programări. Modulul de pacienți permite înregistrarea, actualizarea și arhivarea datelor demografice, alături de o funcție de căutare rapidă. Sistemul de programări facilitează crearea și modificarea întâlnirilor, oferind vizualizări calendaristice pentru fiecare medic. La nivel clinic, aplicația permite completarea fișelor de consultație, menținerea unui istoric medical complex (afecțiuni cronice, alergii, vaccinări) și emiterea rețetelor asociate vizitelor.

### Arhitectura Bazei de Date

Baza de date este implementată în Microsoft SQL și e formată din șapte tabele principale: Pacienti, Medici, Programari, Consultatii, Afectiuni, PacientiAfectiuni și Retete. Arhitectura separă intenționat programările de consultații, permițând astfel înregistrarea programărilor anulate care nu s-au concretizat, dar și a consultațiilor neprogramate. Relațiile de tip "many-to-many" dintre pacienți și bolile acestora sunt rezolvate printr-o tabelă de legătură (PacientiAfectiuni), asigurând o mapare corectă a istoricului.

### Rapoarte și Statistici
Sistemul include un modul avansat de tip Dashboard care folosește interogări SQL (simple și cu subcereri) pentru a extrage informații analitice:
* Generarea unui top al medicilor în funcție de volumul de muncă total.
* Identificarea zilelor cu activitate clinică intensă, în care programările depășesc media zilnică.
* Filtrarea pacienților complecși diagnosticați cu afecțiuni multiple sau a celor fără istoric medical activ.
* Urmărirea pacienților cu un istoric de anulări frecvente și centralizarea rețetelor prescrise.
