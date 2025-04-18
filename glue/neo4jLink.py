      
import os
import json
import sys
from pymongo import MongoClient, errors as pymongo_errors # Import specifico per errori
from neo4j import GraphDatabase, basic_auth, exceptions as neo4j_exceptions # Import specifico per errori
from urllib.parse import quote_plus
import traceback # Import per stack trace

# --- Configuration from Environment Variables ---
# !!! LE CREDENZIALI SONO HARDCODED COME RICHIESTO - NON RACCOMANDATO PER PRODUZIONE !!!
MONGO_DB_NAME = "unibg_tedx_2025"
MONGO_COLLECTION_NAME = "tedx_data"
MONGO_USER = "poldo"
MONGO_PASSWORD = "*@78t@%2%^#8nZC6p$3Z"
MONGO_HOST = "cluster0.izou0.mongodb.net"

NEO4J_URI = "neo4j+s://05a32e55.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "DrwcO69OFVN2olZl9VsPRT_f8r_oGyl3TXVZvUkGgoQ"

# --- Basic Validation ---
# Aggiungi i nuovi campi Mongo alla validazione
if not all([MONGO_USER, MONGO_PASSWORD, MONO_HOST, MONGO_DB_NAME, MONGO_COLLECTION_NAME,
            NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD]):
    print("Error: Missing one or more configuration variables (MONGO_*, NEO4J_*)")
    # In Glue, esci con un codice di errore per segnalare il fallimento del job
    sys.exit("Configuration Error: Missing required variables.")

# --- Global Clients (initialized outside main logic for clarity) ---
mongo_client = None
neo4j_driver = None

# --- Client Initialization Function ---
def init_clients():
    """Initializes MongoDB and Neo4j clients if not already initialized."""
    global mongo_client, neo4j_driver

    # --- MongoDB Initialization ---
    if mongo_client is None:
        try:
            print("Initializing MongoDB client...")
            encoded_user = quote_plus(MONGO_USER)
            encoded_password = quote_plus(MONGO_PASSWORD)
            mongo_uri_string = f"mongodb+srv://{encoded_user}:{encoded_password}@{MONGO_HOST}/?retryWrites=true&w=majority"
            print(f"Connecting to MongoDB host: {MONGO_HOST}")
            # Aumenta leggermente il timeout per Glue se necessario
            mongo_client = MongoClient(mongo_uri_string, serverSelectionTimeoutMS=10000)
            mongo_client.admin.command('ping') # Verifica la connessione
            print("MongoDB connection successful.")
        except (pymongo_errors.ConfigurationError, pymongo_errors.ConnectionFailure) as e:
            print(f"Error connecting to MongoDB: {e}")
            mongo_client = None
            raise # Rilancia l'eccezione per fermare l'esecuzione
        except Exception as e:
            print(f"An unexpected error occurred during MongoDB initialization: {e}")
            mongo_client = None
            raise

    # --- Neo4j Initialization ---
    if neo4j_driver is None:
        try:
            print("Initializing Neo4j driver...")
            neo4j_driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD),
                connection_timeout=20 # Aumenta leggermente il timeout per Glue se necessario
            )
            neo4j_driver.verify_connectivity()
            print("Neo4j connection successful.")
        except (neo4j_exceptions.ServiceUnavailable, neo4j_exceptions.AuthError) as e:
            print(f"Error connecting to Neo4j: {e}")
            neo4j_driver = None
            raise # Rilancia l'eccezione per fermare l'esecuzione
        except Exception as e:
            print(f"An unexpected error occurred during Neo4j initialization: {e}")
            neo4j_driver = None
            raise

# --- Client Cleanup Function ---
def cleanup_clients():
    """Closes Neo4j driver connection."""
    global neo4j_driver
    if neo4j_driver:
        try:
            print("Closing Neo4j driver.")
            neo4j_driver.close()
            neo4j_driver = None
        except Exception as e:
            print(f"Warning: Error closing Neo4j driver: {e}") # Logga l'errore ma non bloccare
    # Il client Mongo gestisce il pool, non serve chiuderlo esplicitamente qui

# --- Neo4j Query Functions ---
def create_or_update_talk_node(tx, talk_data):
    """
    Uses MERGE to create a Talk node or update properties.
    Uses 'id' property derived from MongoDB '_id'.
    """
    talk_id = str(talk_data['_id']) # Assicura che sia stringa
    # Pulisci le proprietà: escludi _id, next_watch e valori None.
    # Assicurati che i tipi siano compatibili con Neo4j.
    props = {}
    for k, v in talk_data.items():
        if k not in ['_id', 'next_watch'] and v is not None:
            # Esempio: Assicurati che le liste contengano solo primitivi
            if isinstance(v, list):
                props[k] = [item for item in v if isinstance(item, (str, int, float, bool))]
            elif isinstance(v, (str, int, float, bool)):
                 props[k] = v
            # Altrimenti, ignora tipi complessi non gestiti (es. dict annidati)
            # Potresti dover aggiungere logica specifica qui per i tuoi dati

    # --- Gestione Tipi Specifica (esempio 'duration') ---
    if 'duration' in props:
        try:
            if isinstance(props['duration'], str) and props['duration'].isdigit():
                props['duration'] = int(props['duration'])
            elif isinstance(props['duration'], (int, float)):
                 props['duration'] = int(props['duration'])
            else:
                 print(f"Warning: Could not convert duration '{props.get('duration')}' to int for talk {talk_id}. Removing property.")
                 del props['duration']
        except (ValueError, TypeError):
            print(f"Warning: Error converting duration '{props.get('duration')}' for talk {talk_id}. Removing property.")
            if 'duration' in props: del props['duration']

    # Aggiungi altre conversioni/pulizie qui...

    query = (
        "MERGE (t:Talk {id: $talk_id}) "
        "ON CREATE SET t = $props, t.id = $talk_id "
        "ON MATCH SET t += $props, t.id = $talk_id "
    )
    tx.run(query, talk_id=talk_id, props=props)

def create_relationship(tx, source_talk_id, related_talk_id):
    """
    Uses MERGE to create a RELATED_TO relationship between two Talk nodes.
    """
    source_id_str = str(source_talk_id)
    related_id_str = str(related_talk_id)

    # Verifica che related_id_str non sia vuoto o problematico
    if not related_id_str:
        print(f"Warning: Attempted to create relationship from {source_id_str} to an empty related_id. Skipping.")
        return # Non eseguire la query se l'ID correlato non è valido

    query = (
        "MATCH (source:Talk {id: $source_id}) "
        "MATCH (related:Talk {id: $related_id}) "
        "WHERE related.id IS NOT NULL " # Aggiunta sicurezza: assicurati che il nodo correlato esista
        "MERGE (source)-[:RELATED_TO]->(related)"
    )
    try:
        result = tx.run(query, source_id=source_id_str, related_id=related_id_str)
        summary = result.consume()
        # Puoi aggiungere log qui basati su summary.counters se necessario
    except Exception as e:
        # Potrebbe fallire se uno dei MATCH non trova il nodo (es. ID errato, nodo non creato)
        print(f"Error executing relationship MERGE ({source_id_str})->({related_id_str}): {e}. Skipping this relationship.")
        # Non rilanciare l'eccezione qui per permettere al job di continuare con altre relazioni

# --- Main Execution Logic for Glue Python Shell ---
if __name__ == "__main__":

    print("Starting AWS Glue Python Shell Job...")
    processed_nodes = 0
    created_relationships = 0
    clients_initialized_successfully = False # Flag per il blocco finally

    try:
        # --- Initialize Clients ---
        print("Attempting to initialize database clients...")
        init_clients()
        clients_initialized_successfully = True # Se arriva qui, l'init è andato a buon fine
        print("Database clients initialized successfully.")

        # --- Get MongoDB Collection ---
        # Non serve controllare se i client sono None qui, init_clients lancia eccezione se fallisce
        db = mongo_client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION_NAME]
        print(f"Accessed MongoDB collection: {MONGO_DB_NAME}.{MONGO_COLLECTION_NAME}")

        # --- Fetch Data ---
        print("Fetching talks data from MongoDB...")
        try:
             # Considera find({}).limit(N) per testare con pochi dati
             # Considera proiezione se non servono tutti i campi: collection.find({}, {'_id': 1, 'title': 1, 'next_watch': 1, ...})
             talks_cursor = collection.find({})
             talks_data = list(talks_cursor) # ATTENZIONE: Carica tutto in memoria! Ok per dati < memoria worker Glue
             found_count = len(talks_data)
             print(f"Found {found_count} talks in MongoDB.")
             if not talks_data:
                 print("No data found in MongoDB collection. Job will exit successfully.")
                 # Uscire qui se non c'è nulla da fare è corretto
             else:
                # --- Phase 1: Create/Update Nodes ---
                print("Phase 1: Creating/Updating Talk nodes in Neo4j...")
                with neo4j_driver.session(database="neo4j") as session: # Specifica il database Neo4j target
                    for i, talk in enumerate(talks_data):
                        if '_id' not in talk or talk['_id'] is None:
                            print(f"Skipping document at index {i} due to missing or null '_id'.")
                            continue
                        try:
                            # Usa execute_write per la gestione automatica delle transazioni e dei retry
                            session.execute_write(create_or_update_talk_node, talk)
                            processed_nodes += 1
                            if processed_nodes % 100 == 0 or processed_nodes == found_count:
                                print(f"Processed {processed_nodes}/{found_count} nodes...")
                        except Exception as e:
                            # Logga l'errore ma continua con gli altri nodi
                            print(f"Error processing node for talk ID {talk.get('_id', 'N/A')}: {e}")
                            traceback.print_exc() # Stampa lo stack trace per debug
                            # Potresti voler salvare gli ID falliti per un'analisi successiva
                            continue
                print(f"Finished Phase 1. Processed {processed_nodes} nodes.")

                # --- Phase 2: Create Relationships ---
                print("Phase 2: Creating RELATED_TO relationships in Neo4j...")
                with neo4j_driver.session(database="neo4j") as session:
                     for i, talk in enumerate(talks_data):
                         source_id = talk.get('_id')
                         next_watch_list = talk.get('next_watch')

                         if not source_id:
                             print(f"Skipping relationship creation for talk at index {i} without source ID.")
                             continue

                         # Assicurati che 'next_watch' sia una lista e non None/vuota
                         if isinstance(next_watch_list, list) and next_watch_list:
                             for related_id in next_watch_list:
                                 # Salta auto-relazioni e valori None/vuoti nella lista
                                 if related_id is None or str(related_id).strip() == "" or str(source_id) == str(related_id):
                                     if str(source_id) == str(related_id):
                                         # print(f"Skipping self-relationship for talk ID {source_id}") # Log opzionale
                                         pass
                                     else:
                                         print(f"Skipping invalid/null related_id '{related_id}' for source {source_id}")
                                     continue

                                 try:
                                     # Usa execute_write anche qui
                                     session.execute_write(create_relationship, source_id, related_id)
                                     created_relationships += 1 # Incrementa qui, anche se MERGE potrebbe non creare nulla di nuovo
                                     if created_relationships % 100 == 0:
                                         print(f"Attempted to create/merge {created_relationships} relationships...")
                                 except Exception as e:
                                     # create_relationship ora gestisce gli errori di query internamente e logga
                                     # Non c'è bisogno di fare molto altro qui, a meno che non si voglia interrompere il job
                                     # Questo punto non dovrebbe essere raggiunto se create_relationship cattura le eccezioni di run()
                                     print(f"Unexpected error during relationship write transaction ({source_id})->({related_id}): {e}")
                                     traceback.print_exc()
                                     continue # Continua con la prossima relazione/talk

                print(f"Finished Phase 2. Attempted to create/merge approximately {created_relationships} relationships (MERGE skips duplicates).")
                print("Data synchronization process completed.")

        except Exception as e:
             print(f"Error fetching data from MongoDB or during processing phases: {e}")
             traceback.print_exc()
             # Considera di uscire con errore se il fetch fallisce
             sys.exit("Job failed during data fetching or processing.")


    # --- Gestione Errori Generali (es. Connessione Iniziale) ---
    except (pymongo_errors.ConnectionFailure, neo4j_exceptions.ServiceUnavailable, neo4j_exceptions.AuthError) as e:
        print(f"FATAL: Database connection or authentication error during initialization: {e}")
        traceback.print_exc()
        # Segnala il fallimento del job a Glue
        sys.exit("Job failed due to database connection/auth error.")
    except Exception as e: # Catch generico per altri problemi imprevisti (es. errori di logica nello script)
        print(f"FATAL: An unexpected error occurred: {e}")
        traceback.print_exc()
        # Segnala il fallimento del job a Glue
        sys.exit("Job failed due to an unexpected error.")
    finally:
        # --- Cleanup Clients ---
        # Chiudi i client SOLO se sono stati inizializzati con successo
        if clients_initialized_successfully:
             print("Executing final client cleanup...")
             cleanup_clients()
        else:
             print("Skipping client cleanup as initialization may have failed.")

        print("AWS Glue Python Shell Job Finished.")
        # Se arrivi qui senza sys.exit(1), il job viene considerato SUCCESSFUL

    