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
            driver.verify_connectivity()
            print("Successfully connected to Neo4j.")
        except Exception as e:
            print(f"Error connecting to Neo4j: {e}")
            raise ConnectionError(f"Failed to connect to Neo4j: {e}") from e
    return driver

def search_nodes_by_title_cypher(tx, search_term_param):

    query = (
        "MATCH (n) "
        "WHERE toLower(n.title) CONTAINS toLower($search_term) "
        "RETURN n.id AS id, n.title AS title "
        "ORDER BY n.title " # Opzionale: ordina i risultati, ma non per "affinità"
        "LIMIT 5"
    )

    result = tx.run(query, search_term=search_term_param)
    
    nodes_data = []
    for record in result:
        nodes_data.append({
            "id": record["id"], # Assicurati che i tuoi nodi abbiano una proprietà 'id'
                                # o usa id(n) se vuoi l'ID interno di Neo4j
            "title": record["title"]
        })
    return nodes_data

def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        # Estrai 'search' dal corpo della richiesta (assumendo un POST con corpo JSON)
        body = {}
        try:
            if isinstance(event.get('body'), str):
                body = json.loads(event.get('body', '{}'))
            elif isinstance(event.get('body'), dict): # Già un dizionario (es. test diretto Lambda)
                body = event.get('body', {})
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Invalid JSON in request body'})
            }
            
        search_string = body.get('search')

        if not search_string:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Parameter "search" is missing in the request body'})
            }

        print(f"Searching for nodes with title similar to: {search_string}")

        db_driver = get_neo4j_driver()
        
        found_nodes_list = []
        with db_driver.session() as session:
            found_nodes_list = session.read_transaction(search_nodes_by_title_cypher, search_string)
        
        print(f"Found {len(found_nodes_list)} matching nodes.")

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(found_nodes_list)
        }

    except ConnectionError as ce:
        print(f"Connection Error: {ce}")
        return {
            'statusCode': 503,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Database connection failed', 'details': str(ce)})
        }
    except Exception as e:
        print(f"Error processing request: {e}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal server error', 'details': str(e)})
        }
