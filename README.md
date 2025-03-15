# 🎯 **TEDxGRAPH**
**Titolo del Progetto:** WebApp interattiva in Flutter per l'esplorazione e l'approfondimento dei talk TEDx tramite mappe mentali con AI e trascrizioni integrate.

## 📌 **Indice**
1. [🎯 Obiettivi del Progetto](#-obiettivi-del-progetto)  
2. [🛠️ Funzionalità Principali](#️-funzionalità-principali)  
   - [🧠 Mappe Mentali Interattive](#-mappe-mentali-interattive)  
   - [🔍 Trascrizioni Complete + Ricerca nei Testi](#-trascrizioni-complete--ricerca-nei-testi)  
   - [🤖 Generazione Automatica di Riassunti con AI](#-generazione-automatica-di-riassunti-con-ai)  
   - [💬 Ricerca con NLP](#-ricerca-con-nlp)  
3. [✨ Ulteriori Spunti](#-ulteriori-spunti)  
   - [🎥 Integrazione con Video](#-integrazione-con-video)  
   - [🏆 Gamification & Progressione dell’Utente](#-gamification--progressione-dellutente)  
4. [⚙️ Tecnologie AWS Utilizzate](#️-tecnologie-aws-utilizzate)  
5. [🌟 Esempio di Esperienza Utente](#-esempio-di-esperienza-utente)  

&nbsp;
## 🎯 **Obiettivi del progetto**
Creazione di un'applicazione/WebApp interattiva in **Flutter**, che permetta l'esplorazione e l'approfondimento di tematiche già trattate nei talk di **TEDx**, utilizzando un metodo rappresentativo a grafo per un apprendimento più schematico ed innovativo. Ogni talk viene visualizzato come un nodo di una mappa, con collegamenti ad argomenti correlati (sotto forma di altri grafi o sottografi), permettendo agli utenti di esplorare i talk in modo non lineare, seguendo i propri interessi e scoprendo connessioni inaspettate tra idee e speaker.

&nbsp;
## 🛠️ **Funzionalità Principali**

### 🧠 **Mappe Mentali Interattive**
- Ogni talk è rappresentato da un **nodo centrale**. Gli utenti possono **zoomare**, **spostarsi** e **cliccare** sui nodi per approfondire.
  
  I nodi secondari rappresentano:
  - **Parole chiave** estratte dal titolo, dalla descrizione e dalla trascrizione completa (usando *Amazon Comprehend*).
  - **Speaker correlati** (esempio: speaker che trattano argomenti simili).
  - **Talk su temi affini**.

  Un'esperienza visiva unica che permette agli utenti di esplorare a fondo ogni argomento.

### 🔍 **Trascrizioni Complete + Ricerca nei Testi**
- **AWS Transcribe** per ottenere **trascrizioni accurate** dei talk.
- **Amazon OpenSearch** per una **ricerca semantica** all'interno dei contenuti trascritti.
- Gli utenti possono cercare **frasi specifiche** pronunciate dai speaker.

### 🤖 **Generazione Automatica di Riassunti con AI**
- Utilizzo di **Amazon Bedrock** o **Amazon Comprehend** per generare **riassunti** e **collegamenti** che alimentano la mappa mentale.

### 💬 **Ricerca con NLP**
- Elaborazione del linguaggio naturale (NLP) mediante il servizio **Comprehend**, ad esempio:
  *"Quali talk mi consigli su AI e impatto sociale?"*
  L'AI mostrerà i **nodi pertinenti** e creerà nuovi **link** verso articoli o risorse esterne che trattano temi correlati.

&nbsp;
## ✨ **Ulteriori Spunti**

### 🎥 **Integrazione con Video**
- Cliccando su un nodo, gli utenti possono guardare il **video del talk** direttamente nell'app (integrazione con **YouTube** o **TED.com**).

### 🏆 **Gamification & Progressione dell’Utente**
- **Sistema di badge** e **sfide**:
  - *"Esploratore delle Idee"* (guarda 5 talk su un tema).
  - *"Collezionista di Mappe"* (salva e condivide 3 mappe).
  
- Sistema di **punti** per incentivare l’interazione e la scoperta di nuovi contenuti.

&nbsp;
## ⚙️ **Tecnologie AWS Utilizzate**

1. **Amazon Comprehend**:
   - Per estrarre **parole chiave**, **argomenti** e **sentiment** dai titoli, dalle descrizioni e dalle trascrizioni complete dei talk.

2. **Neo4j AuraDB**:
   - Un **database a grafo** per memorizzare e gestire le relazioni tra talk, speaker, parole chiave e argomenti.

3. **Amazon S3**:
   - Per archiviare i **file CSV** e i metadati dei talk.

4. **AWS Lambda + API Gateway**:
   - Per creare **API** che restituiscano i dati delle mappe mentali all'app **Flutter**.

5. **AWS Transcribe**:
   - Per ottenere **trascrizioni accurate** dei talk TEDx.

6. **Amazon OpenSearch Service**:
   - Per abilitare la **ricerca semantica** nei contenuti trascritti.

7. **Amazon Bedrock**:
   - Per generare **riassunti** con **AI**.

&nbsp;
## 🌟 **Esempio di Esperienza Utente**

### 1. **Apri l'App**
A seguito di una ricerca eseguita dall'utente, viene mostrata una **mappa mentale** con un **nodo centrale** (ad esempio, un talk su "Intelligenza Artificiale").

### 2. **Esplora**
Cliccando sul nodo, si espandono nodi secondari:
  - **Parole chiave**: "Machine Learning", "Etica", "Futuro".
  - **Speaker correlati**: "Andrew Ng", "Fei-Fei Li".
  - **Talk affini**: "Come l'AI sta cambiando il mondo", "Il futuro del lavoro".

### 3. **Scopri**
L'utente clicca su **"Etica"** e trova un talk su **"L'etica dell'AI"** di un altro speaker. La mappa si espande ulteriormente, rivelando nuove connessioni.

### 4. **Cerca**
L'utente ricerca utilizzando un linguaggio naturale che viene analizzato per ottenere un **nodo** che se cliccato espande verso nuovi nodi.

### 5. **Salva e Condividi**
L'utente salva la mappa come "**Viaggio nell'Intelligenza Artificiale**" e la condivide con un amico.
