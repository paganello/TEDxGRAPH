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

def get_connected_nodes(tx, node_id_param):
    query = (
        "MATCH (startNode {id: $node_id_param})--(connectedNode) "
        "RETURN connectedNode.title AS title, "
        "       connectedNode.speakers AS speakers, "
        "       connectedNode.description AS description"
    )
    result = tx.run(query, node_id_param=node_id_param)
    
    nodes_data = []
    for record in result:
        nodes_data.append({
            "title": record["title"],
            "speakers": record["speakers"], # Assumendo sia una lista o una stringa
            "description": record["description"]
        })
    return nodes_data

def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        # Estrai 'id' dai parametri della query string (tipico per GET via API Gateway)
        query_params = event.get('queryStringParameters', {})
        if not query_params: # Prova a vedere se arriva nel body (per POST o test diretti)
            try:
                body = json.loads(event.get('body', '{}'))
                node_id = body.get('id')
            except json.JSONDecodeError:
                node_id = None
        else:
            node_id = query_params.get('id')

        if not node_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*' # Per CORS, adattare se necessario
                },
                'body': json.dumps({'error': 'Parameter "id" is missing'})
            }

        print(f"Querying for connections to node with id: {node_id}")

        # Ottieni il driver
        db_driver = get_neo4j_driver()
        
        connected_nodes_list = []
        with db_driver.session() as session:
            connected_nodes_list = session.read_transaction(get_connected_nodes, node_id)
        
        print(f"Found {len(connected_nodes_list)} connected nodes.")

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*' # Importante per le app mobili/web
            },
            'body': json.dumps(connected_nodes_list)
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
