# TEDxGRAPH – Mappe Mentali Interattive dei Talk TEDx

## Obbiettivi del progetto
Creazione di un applicazione/WebApp interattiva in Flutter, che permetta l'esplorazione e l'approfondimento di tematiche gia trattate nei talk di TEDx, utilizzando un metodo rappresentativo a grafo per un apprendimendo piu schematico ed innovativo. Ogni talk viene visualizzato come un nodo di una mappa, con collegamenti ad argomenti correlati (sotto forma di altri grafi o sottogravi), permettendo agli utenti di esplorare i talk in modo non lineare, seguendo i propri interessi e scoprendo connessioni inaspettate tra idee e speaker.

## Funzionalità Principali

1. **Mappe Mentali Interattive**: Ogni talk è rappresentato come un nodo centrale, gli utenti possono zoomare, spostarsi e cliccare sui nodi per approfondire. I nodi secondari rappresentano:
   - Parole chiave estratte dal titolo, dalla descrizione e dalla trascrizione completa (usando *Amazon Comprehend*).
   - Speaker correlati (ad esempio, speaker che hanno trattato argomenti simili).
   - Talk su temi affini.
   - Gli utenti possono zoomare, spostarsi e cliccare sui nodi per approfondire.

2. **Trascrizioni Complete + Ricerca nei Testi**:
   - Utilizza *AWS Transcribe* per ottenere trascrizioni complete dei talk.
   - Integrazione con *Amazon Kendra* per una ricerca intelligente all'interno dei contenuti.
   - Permette agli utenti di cercare frasi specifiche dette dallo speaker.

3. **Generazione Automatica di Riassunti con AI**:
   Utilizza *Amazon Bedrock* o *Amazon Comprehend* per creare i riassunti e gli approfondimenti/collegamenti che comporranno i nodi della rete.

4. **Assistente AI Conversazionale**:
   L'utente può chiedere ad esempio *"Quali talk mi consigli su AI e impatto sociale?"*, il software mostrera' cosi i nodi pertinenti e creara' grazie all'uso dell'AI nuovi link verso siti web che trattano in modo     piu dettagliato alcuni argomenti citati nei talks.

### Ulteriori spunti 
1. **Integrazione con Video**:
   Cliccando su un nodo, gli utenti possono guardare il video del talk direttamente nell'app (integrazione con YouTube o TED.com).

2. **Gamification & Progressione dell’Utente**:
   Sistema di badge e sfide: *"Esploratore delle Idee"* (guarda 5 talk su un tema), *"Collezionista di Mappe"* (salva e condivide 3 mappe). Sistema di punti per incentivare l’interazione e la scoperta di nuovi contenuti.


## **Tecnologie AWS Utilizzate**

1. **Amazon Comprehend**:
   - Per estrarre parole chiave, argomenti e sentiment dai titoli, dalle descrizioni e dalle trascrizioni complete dei talk.

2. **Amazon Neptune**:
   - Un database di grafi per memorizzare e gestire le relazioni tra talk, speaker, parole chiave e argomenti.

3. **Amazon S3**:
   - Per archiviare i file CSV e i metadati dei talk.

4. **AWS Lambda + API Gateway**:
   - Per creare API che restituiscano i dati delle mappe mentali all'app Flutter.

5. **AWS Transcribe**:
   - Per ottenere trascrizioni accurate dei talk TEDx.

6. **Amazon Kendra**:
   - Per abilitare la ricerca semantica nei contenuti trascritti.

7. **Amazon Bedrock**:
   - Per generare riassunti con AI.

---

## **Esempio di Esperienza Utente**

1. **Apri l'App**: A seguito di una ricerca eseguita dall'utente, viene mostrata una mappa mentale con un nodo centrale (ad esempio, un talk su "Intelligenza Artificiale").

2. **Esplora**: Cliccando sul nodo, si espandono nodi secondari:
     - Parole chiave: "Machine Learning", "Etica", "Futuro".
     - Speaker correlati: "Andrew Ng", "Fei-Fei Li".
     - Talk affini: "Come l'AI sta cambiando il mondo", "Il futuro del lavoro".

3. **Scopri**:
   L'utente clicca su "Etica" e trova un talk su "L'etica dell'AI" di un altro speaker. La mappa si espande ulteriormente, rivelando nuove connessioni.

4. **Chiedi all'AI**:
   L'utente chiede all'assistente AI *"Riassumi questo talk in 3 frasi"* e ottiene un nodo, comprendente i nodi che compongono le 3 frasi, ma che se cliccati espandono verso nuovi nodi.

5. **Salva e Condividi**:
   L'utente salva la mappa come "Viaggio nell'Intelligenza Artificiale" e la condivide con un amico.



