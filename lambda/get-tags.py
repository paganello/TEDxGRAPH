import json
import os
from neo4j import GraphDatabase, basic_auth

# Variabili d'ambiente (da configurare nella Lambda)
NEO4J_URI = os.environ.get('NEO4J_URI')
NEO4J_USER = os.environ.get('NEO4J_USER')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD')

driver = None

def get_neo4j_driver():
    global driver
    if driver is None:
        try:
            driver = GraphDatabase.driver(NEO4J_URI, auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD))
            # Verifica la connessione (opzionale ma utile per il debug iniziale)
            driver.verify_connectivity()
            print("Successfully connected to Neo4j.")
        except Exception as e:
            print(f"Error connecting to Neo4j: {e}")
            # Se la connessione fallisce, driver rimarrà None e gestito dopo
            # Potresti voler sollevare un'eccezione qui se la connessione è critica all'avvio
            raise ConnectionError(f"Failed to connect to Neo4j: {e}") from e
    return driver

def get_all_tags(tx):
    query = """
    MATCH (n)
    WHERE n.tags IS NOT NULL
    UNWIND n.tags AS tag
    RETURN DISTINCT tag
    ORDER BY tag
    """
    result = tx.run(query)
    return [record["tag"] for record in result]



def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        db_driver = get_neo4j_driver()
        with db_driver.session() as session:
            tag_list = session.read_transaction(get_all_tags)
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(tag_list)
        }

    except ConnectionError as ce:
        print(f"Connection Error: {ce}")
        return {
            'statusCode': 503, # Service Unavailable
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Database connection failed', 'details': str(ce)})
        }
    except Exception as e:
        print(f"Error processing request: {e}")
        # Includere str(e) può esporre dettagli, valuta per produzione
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal server error', 'details': str(e)})
        }