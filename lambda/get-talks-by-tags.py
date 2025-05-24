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
        "MATCH (startNode {id: $node_id_param})-->(connectedNode) "
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

def get_talks_by_tags(tx, tags):
    query = """
    MATCH (t:Talk)
    WHERE t.tags IS NOT NULL AND ANY(tag IN $tags WHERE tag IN t.tags)
    RETURN id(t) AS id, t.title AS title, t.speakers AS speakers, t.description AS description, t.tags AS tags
    LIMIT 20
    """
    result = tx.run(query, tags=tags)
    return [
        {
            "id": record["id"],
            "title": record["title"],
            "speakers": record["speakers"],
            "description": record["description"],
            "tags": record["tags"]
        }
        for record in result
    ]

def lambda_handler(event, context):
        print(f"Received event: {event}")

        query_params = event.get('queryStringParameters', {})
        body = {}

        if not query_params:
            try:
                body = json.loads(event.get('body', '{}'))
            except json.JSONDecodeError:
                body = {}

        node_id = query_params.get('id') if query_params else body.get('id')
        tags = query_params.get('tags') if query_params else body.get('tags')

        db_driver = get_neo4j_driver()

        with db_driver.session() as session:
            if tags:
                # Converte la stringa "tag1,tag2" in una lista
                tags_list = [tag.strip() for tag in tags.split(',')] if isinstance(tags, str) else tags
                talks = session.read_transaction(get_talks_by_tags, tags_list)
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps(talks)
                }

            if node_id:
                connected_nodes_list = session.read_transaction(get_connected_nodes, node_id)
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps(connected_nodes_list)
                }

        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Missing required parameters "tags" or "id"'})
        }

