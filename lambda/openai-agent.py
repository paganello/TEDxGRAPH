import json
import os
import requests
from pymongo import MongoClient, errors as pymongo_errors
from bson.objectid import ObjectId # Mantenuto se altre parti del sistema usano ObjectId, anche se per questo specifico _id sembra essere una stringa

# Variabili d'ambiente
MONGODB_CONN_STRING = os.environ.get("MONGODB_CONN_STRING")
MONGODB_DATABASE_NAME = os.environ.get("MONGODB_DATABASE_NAME")
MONGODB_COLLECTION_NAME = os.environ.get("MONGODB_COLLECTION_NAME")
HUGGINGFACE_API_TOKEN = os.environ.get("HUGGINGFACE_API_TOKEN")
HF_MODEL_ID = os.environ.get("HF_MODEL_ID", "mistralai/Mistral-7B-Instruct-v0.3") # O un altro modello adatto per riassunti

mongo_client = None

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

def get_talk_details_from_mongodb(talk_id_str):
    """
    Recupera i dettagli del talk da MongoDB usando un ID stringa.
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
        
        # Basandoci sull'immagine _id: "567505", l'ID è una stringa.
        # Se talk_id_str fosse un ObjectId valido, la query sarebbe ObjectId(talk_id_str)
        query = {"_id": talk_id_str} 

        print(f"Esecuzione query su MongoDB: {query} nella collezione {MONGODB_COLLECTION_NAME}")
        document = collection.find_one(query)

        if document:
            print(f"Documento trovato in MongoDB per l'ID {talk_id_str}")
            # Se _id fosse un ObjectId, convertirlo in stringa per la serializzazione JSON
            if '_id' in document and isinstance(document['_id'], ObjectId):
                document['_id'] = str(document['_id'])
            return document
        else:
            print(f"Nessun documento trovato in MongoDB per l'ID: {talk_id_str} con la query {query}")
            return None
    except Exception as e: # Potrebbe includere bson.errors.InvalidId se si tentasse di convertire una stringa non valida in ObjectId
        print(f"Errore durante l'accesso a MongoDB o ID non valido: {e}")
        return None

# Modificata: nome, parametri, prompt, parametri modello
def get_huggingface_summary(title, transcript_content):
    """
    Chiama le API di Hugging Face Inference per ottenere un riassunto del transcript.
    """
    if not HUGGINGFACE_API_TOKEN:
        print("Errore: HUGGINGFACE_API_TOKEN non impostato.")
        return "Configurazione API mancante."
    if not HF_MODEL_ID:
        print("Errore: HF_MODEL_ID non impostato.")
        return "Configurazione modello mancante."

    api_url = f"https://api-inference.huggingface.co/models/{HF_MODEL_ID}"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"}

    # Nuovo prompt per il riassunto in inglese, basato sul transcript
    prompt_content = f"""
    [INST] You are an expert assistant skilled in summarizing talk content.
    Talk Title: "{title}"
    Talk Transcript: "{transcript_content}"

    Please provide a concise summary of the main topics and key points
    discussed in this talk, based on the provided title and transcript.
    The summary MUST be in English.
    Focus on extracting the core message and relevant information.
    The output should be only the summary text, without any preamble like "Here is the summary:". [/INST]
    """
    # Considera il troncamento se transcript_content è troppo lungo per il modello
    # MAX_PROMPT_LENGTH = 15000 # Esempio, dipende dal modello
    # if len(prompt_content) > MAX_PROMPT_LENGTH:
    #     allowance_for_template = len(prompt_content) - len(transcript_content)
    #     truncate_at = MAX_PROMPT_LENGTH - allowance_for_template - 3 # -3 per "..."
    #     transcript_content_truncated = transcript_content[:truncate_at] + "..."
    #     prompt_content = f"""... (template con transcript_content_truncated) ... """ # Ricostruire il prompt
    #     print(f"Prompt troncato a causa della lunghezza del transcript.")


    payload = {
        "inputs": prompt_content,
        "parameters": {
            "max_new_tokens": 350,      # Adattato per un riassunto (es. ~250-500 parole)
            "temperature": 0.6,         # Leggermente più basso per riassunti fattuali
            "return_full_text": False,  # Solo il testo generato
        },
        "options": {
            "use_cache": True,
            "wait_for_model": True
        }
    }

    print(f"Invio richiesta a Hugging Face API: {api_url} per il modello {HF_MODEL_ID}")
    transcript_preview = transcript_content[:100] + "..." if len(transcript_content) > 100 else transcript_content
    print(f"Payload (title: '{title}', transcript_preview: '{transcript_preview}', ...)")


    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=55) # Timeout per Lambda

        print(f"Hugging Face API Response Status Code: {response.status_code}")
        # print(f"Hugging Face API Response Headers: {response.headers}") # Può essere verboso
        
        response_text_preview = response.text[:500] if response.text else "VUOTO"
        print(f"Hugging Face API Response Text (preview): '{response_text_preview}'")

        if response.status_code == 200:
            try:
                result = response.json()
                if isinstance(result, list) and len(result) > 0 and "generated_text" in result[0]:
                    return result[0]["generated_text"].strip()
                elif isinstance(result, dict) and "generated_text" in result: # Alcuni modelli restituiscono un dict
                    return result["generated_text"].strip()
                elif isinstance(result, dict) and "error" in result:
                    error_msg = result.get("error")
                    estimated_time = result.get("estimated_time")
                    warnings = result.get("warnings")
                    log_msg = f"Hugging Face API ha restituito 200 OK ma con errore JSON (riassunto): {error_msg}"
                    if warnings: log_msg += f" Warnings: {warnings}"
                    print(log_msg)
                    if "Model" in error_msg and "is currently loading" in error_msg and estimated_time is not None:
                        return f"Il modello ({HF_MODEL_ID}) è in fase di caricamento per il riassunto (stimato: {estimated_time}s). Riprova tra poco."
                    return f"Errore da Hugging Face (contenuto in JSON) durante il riassunto: {error_msg}"
                else:
                    print(f"Risposta JSON 200 OK inattesa da Hugging Face API per riassunto: {result}")
                    return "Risposta inattesa dal servizio di riassunto."
            except json.JSONDecodeError as e:
                print(f"Errore nel decodificare la risposta JSON (status 200) da Hugging Face API per riassunto: {e}")
                print(f"Testo della risposta che ha causato l'errore: '{response.text}'")
                return "Errore di comunicazione con il servizio di riassunto (JSON malformato)."
        
        elif response.status_code == 401:
            print(f"Errore di autenticazione (401) con Hugging Face API (riassunto). Controlla HUGGINGFACE_API_TOKEN. Dettagli: {response.text}")
            return "Errore di autenticazione con il servizio di riassunto."
        elif response.status_code == 429:
            print(f"Rate limit superato (429) per Hugging Face API (riassunto). Dettagli: {response.text}")
            return "Limite richieste al servizio di riassunto superato. Riprova più tardi."
        elif response.status_code == 503:
            print(f"Modello Hugging Face ({HF_MODEL_ID}) non disponibile o in caricamento (503) (riassunto). Dettagli: {response.text}")
            try:
                error_detail = response.json()
                if isinstance(error_detail, dict) and "error" in error_detail:
                    error_msg = error_detail.get("error")
                    estimated_time = error_detail.get("estimated_time")
                    if "Model" in error_msg and "is currently loading" in error_msg and estimated_time is not None:
                        return f"Il modello ({HF_MODEL_ID}) per il riassunto è in fase di caricamento (stimato: {estimated_time}s). Riprova tra poco."
                    return f"Servizio di riassunto temporaneamente non disponibile: {error_msg}"
            except json.JSONDecodeError:
                 return f"Servizio di riassunto temporaneamente non disponibile (503). Dettagli: {response.text[:200]}" # Mostra parte del testo se non è JSON
            return "Servizio di riassunto temporaneamente non disponibile (503)." # Fallback
        else:
            print(f"Errore HTTP {response.status_code} da Hugging Face API (riassunto). Dettagli: {response.text}")
            return f"Errore {response.status_code} dal servizio di riassunto. Dettagli: {response.text[:200]}"

    except requests.exceptions.Timeout:
        print("Timeout durante la chiamata a Hugging Face API per riassunto.")
        return "Il servizio di riassunto ha impiegato troppo tempo a rispondere."
    except requests.exceptions.RequestException as req_err:
        print(f"Errore di richiesta generico con Hugging Face API per riassunto: {req_err}")
        return "Errore di connessione con il servizio di riassunto."
    except Exception as e:
        print(f"Errore generico non gestito durante la generazione del riassunto con Hugging Face: {e}")
        import traceback
        traceback.print_exc()
        return "Errore imprevisto durante la generazione del riassunto."

def lambda_handler(event, context):
    """
    Punto di ingresso della funzione Lambda.
    """
    print(f"Evento ricevuto: {json.dumps(event, default=str)}")
    print(f"Variabili d'ambiente MONGODB_CONN_STRING impostata: {'Sì' if MONGODB_CONN_STRING else 'No'}")
    print(f"Variabili d'ambiente HUGGINGFACE_API_TOKEN impostata: {'Sì' if HUGGINGFACE_API_TOKEN else 'No'}")
    print(f"Variabili d'ambiente HF_MODEL_ID: {HF_MODEL_ID}")

    # Header CORS per tutte le risposte
    cors_headers = {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Allow-Methods': 'GET,OPTIONS'}

    # Gestione preflight OPTIONS per CORS
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': cors_headers, 'body': ''}

    talk_id = None
    try:
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
                return {'statusCode': 400, 'headers': {**cors_headers, 'Content-Type': 'application/json'}, 'body': json.dumps({'error': 'Corpo della richiesta JSON non valido'})}
        else:
            talk_id = event.get('id') # Per test console Lambda

        if not talk_id:
            print("Parametro 'id' mancante nella richiesta.")
            return {'statusCode': 400, 'headers': {**cors_headers, 'Content-Type': 'application/json'}, 'body': json.dumps({'error': "Parametro 'id' mancante nella richiesta."})}

        # Assicura che talk_id sia una stringa, come sembra essere nel DB (_id: "567505")
        talk_id = str(talk_id)

        print(f"Recupero dettagli per l'ID (stringa): {talk_id} da MongoDB.")
        talk_details = get_talk_details_from_mongodb(talk_id)

        if not talk_details:
            print(f"Nessun talk trovato con ID: {talk_id} nel database.")
            return {'statusCode': 404, 'headers': {**cors_headers, 'Content-Type': 'application/json'}, 'body': json.dumps({'error': f"Nessun talk trovato con ID: {talk_id} nel database."})}

        title = talk_details.get("title")
        transcript_content = talk_details.get("transcript") # Modifica: usa 'transcript'

        if not title or not transcript_content:
            missing_fields = []
            if not title: missing_fields.append("'title'")
            if not transcript_content: missing_fields.append("'transcript'") # Modifica: controlla 'transcript'
            error_message = f"Dati { ' e '.join(missing_fields) } mancanti per il talk ID: {talk_id} nel database."
            print(error_message)
            # Logga il documento per aiutare a diagnosticare perché i campi sono mancanti
            print(f"Documento recuperato da MongoDB (ID: {talk_id}): {json.dumps(talk_details, default=str)}") 
            return {'statusCode': 400, 'headers': {**cors_headers, 'Content-Type': 'application/json'}, 'body': json.dumps({'error': error_message})}

        print(f"Richiesta di riassunto a Hugging Face per il titolo: '{title}' (transcript preview: '{transcript_content[:100]}...')")
        summary_text = get_huggingface_summary(title, transcript_content) # Modifica: chiama nuova funzione

        # Controllo robusto del risultato della generazione del riassunto
        # I messaggi di errore specifici sono già restituiti da get_huggingface_summary
        # Qui si verifica se la stringa restituita indica un errore noto
        is_error_string = False
        if summary_text:
            summary_lower = summary_text.lower()
            error_keywords = ["errore", "temporaneamente non disponibile", "caricamento", "mancante", "autenticazione", "limite richieste"]
            if any(keyword in summary_lower for keyword in error_keywords):
                is_error_string = True
        
        if not summary_text or is_error_string:
            print(f"Impossibile ottenere il riassunto: {summary_text}")
            status_code = 503 if summary_text and ("caricamento" in summary_text.lower() or "temporaneamente non disponibile" in summary_text.lower()) else 500
            if summary_text and ("configurazione" in summary_text.lower() or "mancante" in summary_text.lower() or "autenticazione" in summary_text.lower()):
                status_code = 500 # Errore di configurazione o autenticazione server-side
            
            error_body = {'error': f"Impossibile ottenere il riassunto. Dettaglio: {summary_text if summary_text else 'Errore sconosciuto dal servizio di riassunto.'}"}
            return {'statusCode': status_code, 'headers': {**cors_headers, 'Content-Type': 'application/json'}, 'body': json.dumps(error_body)}

        # Modifica: aggiorna response_body
        response_body = {
            "talk_id_requested": talk_id,
            "mongodb_document_id": talk_details.get("_id"), # _id dovrebbe essere già stringa
            "original_title": title,
            # "original_transcript_preview": transcript_content[:200] + "..." if transcript_content else None, # Opzionale
            "summary": summary_text # Rinominato da "elaborazione"
        }
        print(f"Riassunto generato con successo per l'ID: {talk_id}")

        return {'statusCode': 200, 'headers': {**cors_headers, 'Content-Type': 'application/json'}, 'body': json.dumps(response_body, ensure_ascii=False)}

    except Exception as e:
        print(f"Errore imprevisto nel lambda_handler: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'statusCode': 500, 'headers': {**cors_headers, 'Content-Type': 'application/json'}, 'body': json.dumps({'error': f'Errore interno del server: {str(e)}'})}