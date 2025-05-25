import json
import os
from neo4j import GraphDatabase, basic_auth

# Variabili d'ambiente (da configurare nelle impostazioni della Lambda)
NEO4J_URI = os.environ.get('NEO4J_URI')
NEO4J_USER = os.environ.get('NEO4J_USER')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD')

# Il driver Neo4j viene inizializzato globalmente per essere riutilizzato
# tra le invocazioni della Lambda (se l'ambiente di esecuzione viene riutilizzato da AWS)
driver = None

def get_neo4j_driver():
    global driver
    if driver is None:
        if not NEO4J_URI or not NEO4J_USER or not NEO4J_PASSWORD:
            print("Errore: Variabili d'ambiente NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD non configurate.")
            raise ValueError("Variabili d'ambiente Neo4j non configurate correttamente.")
        try:
            print(f"Tentativo di connessione a Neo4j URI: {NEO4J_URI}")
            driver = GraphDatabase.driver(NEO4J_URI, auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD))
            # Verifica la connettività per assicurarsi che il driver sia funzionante
            driver.verify_connectivity()
            print("Connessione a Neo4j stabilita con successo.")
        except Exception as e:
            print(f"Errore durante la connessione a Neo4j: {e}")
            # Rilancia l'eccezione per essere gestita dal chiamante (lambda_handler)
            # Questo assicura che driver rimanga None se la connessione fallisce
            driver = None # Assicurati che rimanga None se fallisce
            raise ConnectionError(f"Impossibile connettersi a Neo4j: {e}") from e
    return driver

def get_all_tags(tx):
    """
    Esegue una query Cypher per ottenere tutti i tag distinti dai nodi.
    """
    # Query per estrarre tutti i tag unici dai nodi che hanno una proprietà 'tags'
    # La proprietà 'tags' è assunta essere una lista di stringhe.
    query = """
    MATCH (n)
    WHERE n.tags IS NOT NULL AND size(n.tags) > 0 // Assicura che esista e non sia vuota
    UNWIND n.tags AS tag // Scompatta la lista di tags
    RETURN DISTINCT tag // Restituisce solo i tag unici
    ORDER BY tag // Ordina i tag alfabeticamente
    """
    result = tx.run(query)
    # Estrae il valore 'tag' da ogni record del risultato
    return [record["tag"] for record in result]

def lambda_handler(event, context):
    """
    Funzione principale della Lambda.
    Si connette a Neo4j, recupera tutti i tag e li restituisce come JSON.
    """
    print(f"Evento ricevuto: {json.dumps(event)}")

    try:
        db_driver = get_neo4j_driver() # Ottiene o inizializza il driver

        # Utilizza una sessione per interagire con il database
        # La sessione viene chiusa automaticamente all'uscita dal blocco 'with'
        with db_driver.session() as session:
            # Esegue la transazione in modalità lettura
            tag_list = session.read_transaction(get_all_tags)
        
        print(f"Tag recuperati: {tag_list}")

        # Costruisce la risposta HTTP di successo
        # Il corpo della risposta è una stringa JSON contenente la lista dei tag
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',       # Fondamentale per indicare al client il tipo di contenuto
                'Access-Control-Allow-Origin': '*'        # Permette richieste CORS da qualsiasi origine (da restringere se necessario)
            },
            'body': json.dumps(tag_list) # Serializza la lista di tag in una stringa JSON
        }

    except ValueError as ve: # Errore di configurazione
        print(f"Errore di configurazione: {ve}")
        return {
            'statusCode': 500, # Internal Server Error (o 400 Bad Request se l'errore è dovuto a input)
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Errore di configurazione del servizio', 'details': str(ve)})
        }
    except ConnectionError as ce:
        # Errore specifico di connessione al database
        print(f"Errore di connessione al database: {ce}")
        return {
            'statusCode': 503, # Service Unavailable
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Servizio database non disponibile', 'details': str(ce)})
        }
    except Exception as e:
        # Qualsiasi altra eccezione non gestita
        print(f"Errore durante l'elaborazione della richiesta: {e}")
        # È buona norma loggare l'eccezione completa per il debug (CloudWatch Logs lo farà)
        # Per la risposta al client, è meglio essere generici per non esporre dettagli interni
        return {
            'statusCode': 500, # Internal Server Error
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Errore interno del server', 'details': str(e)}) # Considera di rimuovere str(e) in produzione
        }
