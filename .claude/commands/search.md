Cerca nelle email archiviate usando le API REST.

Per la domanda: $ARGUMENTS

Usa il comando curl appropriato:
- Per ricerca testuale: `curl -s "https://mail.srvc.es/archive/search?q=TERMINE"`
- Per account specifico: `curl -s "https://mail.srvc.es/archive/search?account=ACCOUNT"`
- Per mittente: `curl -s "https://mail.srvc.es/archive/search?from_addr=EMAIL"`
- Per statistiche: `curl -s https://mail.srvc.es/archive/stats`

NON usare tunnel SSH o MySQL direttamente.

Mostra i risultati in modo leggibile.
