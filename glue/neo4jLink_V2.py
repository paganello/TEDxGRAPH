import os
import json
import sys
from pymongo import MongoClient, errors as pymongo_errors # Import specifico per errori
from neo4j import GraphDatabase, basic_auth, exceptions as neo4j_exceptions # Import specifico per errori
from urllib.parse import quote_plus
import traceback # Import per stack trace
from datetime import datetime # Aggiunto per la conversione di publishedAt


# Credenziali da configurare tramite ambiente o secret manager
MONGO_USER = "[inserire il proprio username MongoDB]"
MONGO_PASSWORD = "[inserire la propria password MongoDB]"
MONGO_HOST = "[inserire il proprio host MongoDB, es. cluster0.xxx.mongodb.net]"
MONGO_DB_NAME = "[inserire il nome del database MongoDB, es. unibg_tedx_2025]"
MONGO_COLLECTION_NAME = "[inserire il nome della collezione MongoDB, es. tedx_data]"

NEO4J_URI = "[inserire l'URI Neo4j, es. neo4j+s://... ]"
NEO4J_USER = "[inserire il proprio username Neo4j]"
NEO4J_PASSWORD = "[inserire la propria password Neo4j]"

# --- Basic Validation ---
# Aggiungi i nuovi campi Mongo alla validazione
if not all([MONGO_USER, MONGO_PASSWORD, MONGO_HOST, MONGO_DB_NAME, MONGO_COLLECTION_NAME,
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
    All other fields from MongoDB (except 'next_watch') are set as properties.
    """
    talk_id = str(talk_data['_id']) # Assicura che sia stringa
    
    props = {}
    for k, v in talk_data.items():
        if k not in ['_id', 'next_watch'] and v is not None: # Esclude _id, next_watch e valori null
            if isinstance(v, list):
                # Assicura che le liste contengano solo tipi primitivi supportati da Neo4j
                # o che il driver Python possa convertire (es. str, int, float, bool).
                # Per tipi più complessi in liste, sarebbe necessaria una gestione ad-hoc.
                props[k] = [item for item in v if isinstance(item, (str, int, float, bool))]
            elif isinstance(v, (str, int, float, bool, dict)): # Neo4j supporta mappe (dict)
                 props[k] = v
            # Altri tipi (es. oggetti non serializzabili) verrebbero ignorati.
            # Se ci sono tipi specifici da gestire (es. ObjectId di Mongo non stringhizzati),
            # andrebbero trattati qui.

    # --- Gestione Tipi Specifica ---
    # Duration: converti in intero se è una stringa numerica
    if 'duration' in props and isinstance(props['duration'], str):
        try:
            if props['duration'].isdigit():
                props['duration'] = int(props['duration'])
            else:
                 # Se non è un intero valido, potrebbe essere meglio rimuoverlo o loggare un errore più specifico
                 print(f"Warning: duration '{props['duration']}' for talk {talk_id} is not a simple numeric string. Storing as string or consider specific handling.")
        except ValueError: # Mantenuto per sicurezza, anche se isdigit() dovrebbe coprire
            print(f"Warning: Could not convert duration '{props['duration']}' to int for talk {talk_id}. Storing as string.")
    elif 'duration' in props and not isinstance(props['duration'], (int, float)):
        # Se duration è presente ma non è né stringa né numero (improbabile data la logica sopra)
        print(f"Warning: duration for talk {talk_id} has an unexpected type: {type(props['duration'])}. Removing property.")
        del props['duration']


    # publishedAt: converti in oggetto datetime se è una stringa ISO 8601
    # Il driver Python per Neo4j convertirà l'oggetto datetime di Python
    # nel tipo DateTime di Neo4j.
    if 'publishedAt' in props and isinstance(props['publishedAt'], str):
        try:
            iso_string = props['publishedAt']
            # Python 3.7+ datetime.fromisoformat gestisce 'Z' (UTC Zulu).
            # Per versioni precedenti o per maggiore robustezza con formati leggermente diversi:
            if iso_string.endswith('Z'):
                # Sostituisce 'Z' con '+00:00' che fromisoformat comprende universalmente per UTC
                dt_obj = datetime.fromisoformat(iso_string[:-1] + '+00:00')
            else:
                # Prova a parsare direttamente, sperando sia un formato ISO compatibile
                dt_obj = datetime.fromisoformat(iso_string)
            props['publishedAt'] = dt_obj
        except ValueError:
            print(f"Warning: Could not parse publishedAt string '{props['publishedAt']}' into datetime for talk {talk_id}. It will be stored as a string if possible, or skipped.")
            # Lascia props['publishedAt'] come stringa se il parsing fallisce. Neo4j lo memorizzerà come stringa.
            # Se si preferisce non memorizzare stringhe malformate, si può fare: del props['publishedAt']

    query = (
        "MERGE (t:Talk {id: $talk_id}) "
        "ON CREATE SET t = $props, t.id = $talk_id " # t.id è ridondante se props contiene id, ma sicuro
        "ON MATCH SET t += $props, t.id = $talk_id " # Sovrascrive/aggiunge proprietà, t.id assicura che non venga perso
    )
    tx.run(query, talk_id=talk_id, props=props)


def create_relationship(tx, source_talk_id, related_talk_id):
    """
    Uses MERGE to create a RELATED_TO relationship between two Talk nodes.
    """
    source_id_str = str(source_talk_id)
    related_id_str = str(related_talk_id) # Assicurati che anche related_id sia una stringa

    # Verifica che related_id_str non sia vuoto o problematico
    if not related_id_str: # Questa verifica è già fatta nel loop principale, ma è una doppia sicurezza
        print(f"Warning: Attempted to create relationship from {source_id_str} to an empty related_id. Skipping (inside create_relationship).")
        return

    query = (
        "MATCH (source:Talk {id: $source_id}) "
        "MATCH (related:Talk {id: $related_id}) "
        # Non è necessario "WHERE related.id IS NOT NULL" se $related_id non è mai null o stringa vuota
        # e se c'è un vincolo di esistenza sull'ID o se i nodi sono creati prima.
        # Il MATCH stesso non troverà nodi se l'ID è problematico.
        "MERGE (source)-[:RELATED_TO]->(related)"
    )
    try:
        result = tx.run(query, source_id=source_id_str, related_id=related_id_str)
        summary = result.consume()
        # Logica di conteggio relazioni effettivamente create/unite potrebbe basarsi su summary.counters
    except Exception as e:
        print(f"Error executing relationship MERGE ({source_id_str})->({related_id_str}): {e}. Skipping this relationship.")
        # Non rilanciare l'eccezione per permettere al job di continuare

# --- Main Execution Logic for Glue Python Shell ---
if __name__ == "__main__":

    print("Starting AWS Glue Python Shell Job...")
    processed_nodes = 0
    created_relationships_attempts = 0 # Rinominato per chiarezza, dato che MERGE potrebbe non creare
    clients_initialized_successfully = False

    try:
        print("Attempting to initialize database clients...")
        init_clients()
        clients_initialized_successfully = True
        print("Database clients initialized successfully.")

        db = mongo_client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION_NAME]
        print(f"Accessed MongoDB collection: {MONGO_DB_NAME}.{MONGO_COLLECTION_NAME}")

        print("Fetching talks data from MongoDB...")
        try:
             talks_cursor = collection.find({})
             talks_data = list(talks_cursor)
             found_count = len(talks_data)
             print(f"Found {found_count} talks in MongoDB.")

             if not talks_data:
                 print("No data found in MongoDB collection. Job will exit successfully.")
             else:
                print("Phase 1: Creating/Updating Talk nodes in Neo4j...")
                with neo4j_driver.session(database="neo4j") as session:
                    for i, talk in enumerate(talks_data):
                        if '_id' not in talk or talk['_id'] is None:
                            print(f"Skipping document at index {i} due to missing or null '_id'.")
                            continue
                        try:
                            session.execute_write(create_or_update_talk_node, talk)
                            processed_nodes += 1
                            if processed_nodes % 100 == 0 or processed_nodes == found_count:
                                print(f"Processed {processed_nodes}/{found_count} nodes...")
                        except Exception as e:
                            print(f"Error processing node for talk ID {talk.get('_id', 'N/A')}: {e}")
                            traceback.print_exc()
                            continue
                print(f"Finished Phase 1. Processed {processed_nodes} nodes.")

                print("Phase 2: Creating RELATED_TO relationships in Neo4j...")
                with neo4j_driver.session(database="neo4j") as session:
                     for i, talk in enumerate(talks_data):
                         source_id = talk.get('_id')
                         next_watch_list = talk.get('next_watch')

                         if not source_id:
                             print(f"Skipping relationship creation for talk at index {i} without source ID.")
                             continue

                         if isinstance(next_watch_list, list) and next_watch_list:
                             for related_data_item in next_watch_list:
                                 # Estrai l'ID dal related_data_item.
                                 # Se next_watch contiene direttamente gli ID:
                                 related_id = str(related_data_item) if related_data_item is not None else None
                                 # Se next_watch contiene oggetti, es: {'_id': 'xyz'}, dovresti estrarre l'id:
                                 # related_id = str(related_data_item.get('_id')) if isinstance(related_data_item, dict) and related_data_item.get('_id') is not None else None

                                 if related_id is None or related_id.strip() == "" or str(source_id) == related_id:
                                     if str(source_id) == related_id:
                                         pass # Skip self-relationship
                                     else:
                                         print(f"Skipping invalid/null related_id '{related_id}' for source {source_id}")
                                     continue
                                 
                                 created_relationships_attempts += 1
                                 try:
                                     session.execute_write(create_relationship, source_id, related_id)
                                     if created_relationships_attempts % 100 == 0:
                                         print(f"Attempted to create/merge {created_relationships_attempts} relationships...")
                                 except Exception as e:
                                     # create_relationship gestisce errori di query, questo catch è per errori di transazione
                                     print(f"Unexpected error during relationship write transaction ({source_id})->({related_id}): {e}")
                                     traceback.print_exc()
                                     continue

                print(f"Finished Phase 2. Attempted to create/merge approximately {created_relationships_attempts} relationships (MERGE skips duplicates).")
                print("Data synchronization process completed.")

        except Exception as e:
             print(f"Error fetching data from MongoDB or during processing phases: {e}")
             traceback.print_exc()
             sys.exit("Job failed during data fetching or processing.")

    except (pymongo_errors.ConnectionFailure, neo4j_exceptions.ServiceUnavailable, neo4j_exceptions.AuthError) as e:
        print(f"FATAL: Database connection or authentication error during initialization: {e}")
        traceback.print_exc()
        sys.exit("Job failed due to database connection/auth error.")
    except Exception as e:
        print(f"FATAL: An unexpected error occurred: {e}")
        traceback.print_exc()
        sys.exit("Job failed due to an unexpected error.")
    finally:
        if clients_initialized_successfully:
             print("Executing final client cleanup...")
             cleanup_clients()
        else:
             print("Skipping client cleanup as initialization may have failed.")
        print("AWS Glue Python Shell Job Finished.")