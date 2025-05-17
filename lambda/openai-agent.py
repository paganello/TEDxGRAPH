import json
import os
import requests
from pymongo import MongoClient, errors as pymongo_errors
from bson.objectid import ObjectId

# ... (altre variabili d'ambiente e funzioni MongoDB rimangono invariate) ...
MONGODB_CONN_STRING = os.environ.get("MONGODB_CONN_STRING")
MONGODB_DATABASE_NAME = os.environ.get("MONGODB_DATABASE_NAME")
MONGODB_COLLECTION_NAME = os.environ.get("MONGODB_COLLECTION_NAME")
HUGGINGFACE_API_TOKEN = os.environ.get("HUGGINGFACE_API_TOKEN")
HF_MODEL_ID = os.environ.get("HF_MODEL_ID", "mistralai/Mistral-7B-Instruct-v0.3")

mongo_client = None # Inizializzazione spostata per chiarezza

# ... get_mongodb_client e get_talk_details_from_mongodb rimangono le stesse ...
def get_mongodb_client():
    """
    Inizializza e restituisce il client MongoDB.
    Riutilizza la connessione se già stabilita.
    """
    global mongo_client
    if mongo_client is None:
        if not MONGODB_CONN_STRING:
            print("Errore: la variabile d'ambiente MONGODB_CONN_STRING non è impostata.")
            return None
        try:
            print("Tentativo di connessione a MongoDB...")
            mongo_client = MongoClient(MONGODB_CONN_STRING)
            mongo_client.admin.command('ping')
            print("Connessione a MongoDB stabilita con successo.")
        except pymongo_errors.ConfigurationError as e:
            print(f"Errore di configurazione MongoDB (controlla la stringa di connessione): {e}")
            mongo_client = None
            return None
        except pymongo_errors.ConnectionFailure as e:
            print(f"Impossibile connettersi a MongoDB: {e}")
            mongo_client = None
            return None
        except Exception as e:
            print(f"Errore generico durante la connessione a MongoDB: {e}")
            mongo_client = None
            return None
    return mongo_client

def get_talk_details_from_mongodb(talk_id):
    """
    Recupera i dettagli del talk da MongoDB.
    """
    client = get_mongodb_client()
    if not client:
        return None
    if not MONGODB_DATABASE_NAME or not MONGODB_COLLECTION_NAME:
        print("Errore: MONGODB_DATABASE_NAME o MONGODB_COLLECTION_NAME non impostati.")
        return None

    try:
        db = client[MONGODB_DATABASE_NAME]
        collection = db[MONGODB_COLLECTION_NAME]
        
        query = {"_id": talk_id}
        # Se l'ID che passi deve essere convertito in ObjectId per il campo _id:
        # try:
        #     query = {"_id": ObjectId(talk_id)}
        # except Exception:
        #     print(f"L'ID '{talk_id}' non è un ObjectId valido.")
        #     return None

        print(f"Esecuzione query su MongoDB: {query} nella collezione {MONGODB_COLLECTION_NAME}")
        document = collection.find_one(query)

        if document:
            print(f"Documento trovato in MongoDB per l'ID {talk_id}")
            if '_id' in document and isinstance(document['_id'], ObjectId):
                document['_id'] = str(document['_id'])
            return document
        else:
            print(f"Nessun documento trovato in MongoDB per l'ID: {talk_id} con la query {query}")
            return None
    except Exception as e:
        print(f"Errore durante l'accesso a MongoDB: {e}")
        return None

def get_huggingface_elaboration(title, description):
    """
    Chiama le API di Hugging Face Inference per ottenere un approfondimento.
    """
    if not HUGGINGFACE_API_TOKEN:
        print("Errore: HUGGINGFACE_API_TOKEN non impostato.")
        return "Configurazione API mancante." # Messaggio più specifico per il chiamante
    if not HF_MODEL_ID:
        print("Errore: HF_MODEL_ID non impostato.")
        return "Configurazione modello mancante." # Messaggio più specifico

    api_url = f"https://api-inference.huggingface.co/models/{HF_MODEL_ID}"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"}

    prompt_content = f"""
    [INST] Sei un assistente esperto nell'analizzare e approfondire contenuti di talk.
    Titolo del talk: "{title}"
    Descrizione del talk: "{description}"

    Per favore, approfondisci gli argomenti principali, i temi chiave e le possibili implicazioni
    trattati in questo talk, basandoti sul titolo e sulla descrizione forniti.
    Fornisci un'analisi dettagliata e riflessioni aggiuntive.
    Rispondi in italiano. [/INST]
    """
    payload = {
        "inputs": prompt_content,
        "parameters": {
            "max_new_tokens": 1000,
            "temperature": 0.7,
            "return_full_text": False,
        },
        "options": {
            "use_cache": True,
            "wait_for_model": True # Importante per evitare errori 503 se il modello è freddo
                                   # Aumenta la latenza della prima chiamata, considera il timeout Lambda
        }
    }

    print(f"Invio richiesta a Hugging Face API: {api_url} per il modello {HF_MODEL_ID}")
    print(f"Payload (prime 100 char del prompt): {{'inputs': '{prompt_content[:100]}...', ...}}")

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=55) # Aumentato timeout

        print(f"Hugging Face API Response Status Code: {response.status_code}")
        print(f"Hugging Face API Response Headers: {response.headers.get('Content-Type', 'N/A')}")
        
        # Logga sempre il testo della risposta se non è troppo lungo, per debug
        response_text_preview = response.text[:500] if response.text else "VUOTO"
        print(f"Hugging Face API Response Text (preview): '{response_text_preview}'")

        if response.status_code == 200:
            try:
                result = response.json() # Qui può avvenire l'errore "Expecting value"
                if isinstance(result, list) and len(result) > 0 and "generated_text" in result[0]:
                    return result[0]["generated_text"].strip()
                elif isinstance(result, dict) and "generated_text" in result:
                    return result["generated_text"].strip()
                # Caso in cui la risposta è 200 OK ma contiene un errore JSON da HF
                elif isinstance(result, dict) and "error" in result:
                    error_msg = result.get("error")
                    estimated_time = result.get("estimated_time")
                    warnings = result.get("warnings")
                    log_msg = f"Hugging Face API ha restituito 200 OK ma con errore JSON: {error_msg}"
                    if warnings: log_msg += f" Warnings: {warnings}"
                    print(log_msg)
                    if "Model" in error_msg and "is currently loading" in error_msg and estimated_time is not None:
                        return f"Il modello ({HF_MODEL_ID}) è in fase di caricamento (stimato: {estimated_time}s). Riprova tra poco."
                    return f"Errore da Hugging Face (contenuto in JSON): {error_msg}"
                else:
                    print(f"Risposta JSON 200 OK inattesa da Hugging Face API: {result}")
                    return "Risposta inattesa dal servizio di elaborazione."
            except json.JSONDecodeError as e:
                print(f"Errore nel decodificare la risposta JSON (status 200) da Hugging Face API: {e}")
                print(f"Testo della risposta che ha causato l'errore: '{response.text}'")
                return "Errore di comunicazione con il servizio di elaborazione (JSON malformato)."
        
        # Gestione errori HTTP specifici
        elif response.status_code == 401:
            print(f"Errore di autenticazione con Hugging Face API (401). Controlla HUGGINGFACE_API_TOKEN. Dettagli: {response.text}")
            return "Errore di autenticazione con il servizio di elaborazione."
        elif response.status_code == 429:
            print(f"Rate limit superato per Hugging Face API (429). Dettagli: {response.text}")
            return "Limite richieste al servizio di elaborazione superato. Riprova più tardi."
        elif response.status_code == 503: # Model is loading or service unavailable
            print(f"Modello Hugging Face ({HF_MODEL_ID}) non disponibile o in caricamento (503). Dettagli: {response.text}")
            # Prova a parsare l'errore JSON se presente
            try:
                error_detail = response.json()
                if isinstance(error_detail, dict) and "error" in error_detail:
                    error_msg = error_detail.get("error")
                    estimated_time = error_detail.get("estimated_time")
                    if "Model" in error_msg and "is currently loading" in error_msg and estimated_time is not None:
                        return f"Il modello ({HF_MODEL_ID}) è in fase di caricamento (stimato: {estimated_time}s). Riprova tra poco."
                    return f"Servizio di elaborazione temporaneamente non disponibile: {error_msg}"
            except json.JSONDecodeError:
                # Se non è JSON, restituisci un messaggio generico basato sul testo
                return f"Servizio di elaborazione temporaneamente non disponibile (503). Dettagli: {response.text[:200]}"
            return "Servizio di elaborazione temporaneamente non disponibile (503)." # Fallback
        else:
            # Altri errori HTTP
            print(f"Errore HTTP {response.status_code} da Hugging Face API. Dettagli: {response.text}")
            response.raise_for_status() # Solleva eccezione per essere catturata sotto
            return f"Errore {response.status_code} dal servizio di elaborazione." # Non dovrebbe arrivare qui se raise_for_status funziona

    except requests.exceptions.Timeout:
        print("Timeout durante la chiamata a Hugging Face API.")
        return "Il servizio di elaborazione ha impiegato troppo tempo a rispondere."
    except requests.exceptions.RequestException as req_err: # Cattura altri errori di `requests`
        print(f"Errore di richiesta generico con Hugging Face API: {req_err}")
        return "Errore di connessione con il servizio di elaborazione."
    except Exception as e: # Catch-all per errori imprevisti nella logica di questa funzione
        print(f"Errore generico non gestito durante l'elaborazione con Hugging Face: {e}")
        import traceback
        traceback.print_exc()
        return "Errore imprevisto durante l'elaborazione del testo."

def lambda_handler(event, context):
    """
    Punto di ingresso della funzione Lambda.
    """
    print(f"Evento ricevuto: {json.dumps(event, default=str)}") # Logga l'evento per debug
    print(f"Variabili d'ambiente MONGODB_CONN_STRING impostata: {'Sì' if MONGODB_CONN_STRING else 'No'}")
    print(f"Variabili d'ambiente HUGGINGFACE_API_TOKEN impostata: {'Sì' if HUGGINGFACE_API_TOKEN else 'No'}")
    print(f"Variabili d'ambiente HF_MODEL_ID: {HF_MODEL_ID}")

    talk_id = None
    try:
        # Estrazione dell'ID in modo più robusto
        if isinstance(event.get('queryStringParameters'), dict) and 'id' in event['queryStringParameters']:
            talk_id = event['queryStringParameters']['id']
        elif isinstance(event.get('pathParameters'), dict) and 'id' in event['pathParameters']:
            talk_id = event['pathParameters']['id']
        elif event.get('body'):
            try:
                body = json.loads(event['body'])
                talk_id = body.get('id')
            except json.JSONDecodeError:
                print("Corpo della richiesta JSON non valido.")
                return {'statusCode': 400, 'headers': {'Content-Type': 'application/json'}, 'body': json.dumps({'error': 'Corpo della richiesta JSON non valido'})}
        else: # Tentativo finale se l'ID è direttamente nel payload dell'evento (es. test console Lambda)
            talk_id = event.get('id')

        if not talk_id:
            print("Parametro 'id' mancante nella richiesta.")
            return {'statusCode': 400, 'headers': {'Content-Type': 'application/json'}, 'body': json.dumps({'error': "Parametro 'id' mancante nella richiesta."})}

        print(f"Recupero dettagli per l'ID: {talk_id} da MongoDB.")
        talk_details = get_talk_details_from_mongodb(talk_id)

        if not talk_details:
            print(f"Nessun talk trovato con ID: {talk_id} nel database.")
            return {'statusCode': 404, 'headers': {'Content-Type': 'application/json'}, 'body': json.dumps({'error': f"Nessun talk trovato con ID: {talk_id} nel database."})}

        title = talk_details.get("title")
        description = talk_details.get("description")

        if not title or not description:
            error_message = f"Dati 'title' o 'description' mancanti per il talk ID: {talk_id} nel database."
            print(error_message)
            print(f"Documento recuperato da MongoDB: {talk_details}")
            return {'statusCode': 400, 'headers': {'Content-Type': 'application/json'}, 'body': json.dumps({'error': error_message})}

        print(f"Richiesta di elaborazione a Hugging Face per il titolo: '{title}'")
        elaborated_text = get_huggingface_elaboration(title, description)

        # Controlla se elaborated_text indica un errore noto o è vuoto/None
        # La funzione get_huggingface_elaboration ora restituisce stringhe di errore leggibili
        # oppure il testo elaborato, oppure None in caso di errore non gestito esplicitamente come stringa.
        if not elaborated_text or "errore" in elaborated_text.lower() or "temporaneamente non disponibile" in elaborated_text.lower() or "caricamento" in elaborated_text.lower():
            # Potresti voler mappare questi messaggi a status code diversi, es. 503 per "caricamento"
            print(f"Impossibile ottenere l'approfondimento: {elaborated_text}")
            status_code = 503 if "caricamento" in elaborated_text.lower() or "temporaneamente non disponibile" in elaborated_text.lower() else 500
            return {'statusCode': status_code, 'headers': {'Content-Type': 'application/json'}, 'body': json.dumps({'error': f"Impossibile ottenere l'approfondimento. Dettaglio: {elaborated_text if elaborated_text else 'Errore sconosciuto dal servizio di elaborazione.'}"})}

        response_body = {
            "talk_id_requested": talk_id,
            "mongodb_document_id": talk_details.get("_id"),
            "original_title": title,
            "original_description": description,
            "elaborazione": elaborated_text
        }
        print(f"Risposta inviata con successo per l'ID: {talk_id}")

        return {'statusCode': 200, 'headers': {'Content-Type': 'application/json'}, 'body': json.dumps(response_body, ensure_ascii=False)}

    except Exception as e:
        print(f"Errore imprevisto nel lambda_handler: {str(e)}")
        import traceback
        traceback.print_exc() # Questo stamperà il traceback completo nei log di CloudWatch
        # L'errore originale (e) potrebbe essere l'eccezione json.JSONDecodeError
        # Se arriva qui, significa che è avvenuto fuori dai try/except specifici.
        return {'statusCode': 500, 'headers': {'Content-Type': 'application/json'}, 'body': json.dumps({'error': f'Errore interno del server: {str(e)}'})}
