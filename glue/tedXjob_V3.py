import sys
import json
import requests

from pyspark.sql.functions import col, collect_list, array_join, explode, collect_set, lit, coalesce, array, count, slice, rank, udf
from pyspark.sql.window import Window
from pyspark.sql.types import ArrayType, StringType 

from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.dynamicframe import DynamicFrame
from awsglue.job import Job

##### FROM FILES
tedx_dataset_path = "s3://tedx-2025-data-mp-provaprova/final_list.csv"

###### READ PARAMETERS
args = getResolvedOptions(sys.argv, ['JOB_NAME'])

##### START JOB CONTEXT AND JOB
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# --- INIZIO NUOVA FUNZIONALITÀ: TRASCRIZIONE ---
GRAPHQL_URL = 'https://www.ted.com/graphql'
COMMON_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:138.0) Gecko/20100101 Firefox/138.0',
    'Accept': '*/*',
    'Accept-Language': 'it-IT,en;q=0.7,en-US;q=0.3', # Lingua italiana prioritaria
    'client-id': 'Zenith production',
    'content-type': 'application/json',
    'Origin': 'https://www.ted.com',
    'Referer': 'https://www.ted.com/' # Referer generico, verrà sovrascritto
}

GRAPHQL_QUERY_TEMPLATE = """
query Transcript($id: ID!, $language: String!) {
  translation(videoId: $id, language: $language) {
    paragraphs {
      cues {
        text
        __typename
      }
      __typename
    }
    __typename
  }
}
"""

def fetch_transcript_for_talk(talk_slug, language="it"): # Default alla lingua italiana
    if not talk_slug:
        # print(f"Skipping transcript fetch: talk_slug is null or empty.") # Debug
        return None
    
    payload = {
        "operationName": "Transcript",
        "variables": {
            "id": talk_slug,
            "language": language
        },
        "query": GRAPHQL_QUERY_TEMPLATE
    }
    
    headers = COMMON_HEADERS.copy()
    headers['Referer'] = f'https://www.ted.com/talks/{talk_slug}/transcript?language={language}'
    # Aggiorniamo Accept-Language per dare priorità alla lingua richiesta dalla funzione
    headers['Accept-Language'] = f"{language},en;q=0.7,en-US;q=0.3"


    try:
        # print(f"Fetching transcript for talk_slug: {talk_slug} with language: {language}") # Debug
        response = requests.post(GRAPHQL_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status() # Solleva eccezione per status code HTTP 4xx/5xx
        
        data = response.json()
        
        if data.get("errors"):
            # print(f"GraphQL error for {talk_slug} (lang {language}): {data['errors']}") # Debug
            return None

        translation_block = data.get("data", {}).get("translation") 
        if not translation_block: 
            # print(f"Translation block not found or empty for {talk_slug}, lang {language}.") # Debug
            return None 
        
        paragraphs = translation_block.get("paragraphs")
        
        if not paragraphs:
            # print(f"No paragraphs found for {talk_slug}, lang {language}.") # Debug
            return None 

        transcript_parts = []
        for paragraph in paragraphs:
            # Aggiunto controllo per assicurarsi che paragraph sia un dizionario e abbia 'cues'
            if isinstance(paragraph, dict) and paragraph.get("cues"):
                for cue in paragraph.get("cues", []): # Default a lista vuota se 'cues' non c'è o è None
                    # Aggiunto controllo per assicurarsi che cue sia un dizionario
                    if isinstance(cue, dict):
                        text_content = cue.get("text")
                        if text_content: # Assicura che text_content non sia None o stringa vuota
                            transcript_parts.append(text_content.strip()) # .strip() per pulire
        
        if not transcript_parts: # Se nessuna parte di testo è stata aggiunta
            # print(f"Empty transcript after processing for {talk_slug}, lang {language}.") # Debug
            return None
            
        # SCEGLI COME VUOI UNIRE LE PARTI: con spazio o con a capo
        # full_transcript = " ".join(transcript_parts) # Trascrizione su una riga
        full_transcript = "\n".join(transcript_parts) # Trascrizione con a capo (come nei test)
        return full_transcript
            
    except requests.exceptions.Timeout:
        # print(f"Timeout fetching transcript for {talk_slug}") # Debug
        return None
    except requests.exceptions.RequestException as e:
        # print(f"RequestException fetching transcript for talk_slug {talk_slug}: {e}") # Debug
        return None
    except json.JSONDecodeError as e:
        # print(f"JSONDecodeError for talk_slug {talk_slug}: {e}. Response: {response.text[:200]}") # Debug
        return None
    except Exception as e: # Cattura qualsiasi altra eccezione imprevista
        # print(f"An unexpected error occurred for talk_slug {talk_slug}: {e}") # Debug
        return None

# Registra la funzione come UDF
get_transcript_udf = udf(fetch_transcript_for_talk, StringType())

# --- FINE NUOVA FUNZIONALITÀ: TRASCRIZIONE ---


#### READ INPUT FILES TO CREATE AN INPUT DATASET
tedx_dataset = spark.read \
    .option("header","true") \
    .option("quote", "\"") \
    .option("escape", "\"") \
    .csv(tedx_dataset_path)

# tedx_dataset.printSchema() # Controlla i nomi delle colonne letti dal CSV

if 'slug' in tedx_dataset.columns:
    print("Colonna 'slug' trovata. Recupero delle trascrizioni in corso... questo potrebbe richiedere tempo.")
    tedx_dataset = tedx_dataset.withColumn("transcript", get_transcript_udf(col("slug"))) # Lingua default "it"
    # Per debug, mostra alcuni slug e le loro trascrizioni (o None se non trovate)
    # tedx_dataset.select("slug", "transcript").show(10, truncate=50)
else:
    print("Errore: colonna 'slug' non trovata in tedx_dataset. Impossibile recuperare le trascrizioni.")
    tedx_dataset = tedx_dataset.withColumn("transcript", lit(None).cast(StringType())) # Aggiungi colonna vuota

# tedx_dataset.printSchema() # Controlla che 'transcript' sia stata aggiunta

#### FILTER ITEMS WITH NULL POSTING KEY (colonna "id" numerico)
count_items = tedx_dataset.count()
if 'id' in tedx_dataset.columns:
    count_items_null = tedx_dataset.filter(col("id").isNotNull()).count()
    print(f"Numero di item da RAW DATA {count_items}")
    print(f"Numero di item da RAW DATA con KEY NON NULLA {count_items_null}")
    tedx_dataset = tedx_dataset.filter(col("id").isNotNull()) 
else:
    print("Attenzione: colonna 'id' (numerica) non trovata in tedx_dataset. Salto il controllo delle chiavi nulle.")
    print(f"Numero di item da RAW DATA {count_items}")


## READ THE DETAILS
details_dataset_path = "s3://tedx-2025-data-mp-provaprova/details.csv"
details_dataset = spark.read \
    .option("header","true") \
    .option("quote", "\"") \
    .option("escape", "\"") \
    .csv(details_dataset_path)

details_dataset = details_dataset.select(col("id").alias("id_ref"), # Questo è l'ID numerico per il join
                                             col("description"),
                                             col("duration"),
                                             col("publishedAt"))

# AND JOIN WITH THE MAIN TABLE
tedx_dataset_main = tedx_dataset.join(details_dataset, tedx_dataset["id"] == details_dataset["id_ref"], "left") \
            .drop("id_ref")

# tedx_dataset_main.printSchema()


## READ TAGS DATASET
tags_dataset_path = "s3://tedx-2025-data-mp-provaprova/tags.csv"
tags_dataset = spark.read.option("header","true").csv(tags_dataset_path)

tedx_final_dataset = None # Inizializza per sicurezza

if 'id' in tags_dataset.columns and 'tag' in tags_dataset.columns:
    print("Filtraggio tag comuni...")
    tag_threshold = 500
    tag_counts = tags_dataset.groupBy("tag").agg(count("*").alias("tag_occurrence"))
    
    print(f"Tag unici totali prima del filtraggio: {tag_counts.count()}")
    filtered_tag_counts = tag_counts.filter(col("tag_occurrence") <= tag_threshold)
    print(f"Tag unici totali dopo il filtraggio (<= {tag_threshold} occorrenze): {filtered_tag_counts.count()}")

    tags_dataset_filtered = tags_dataset.join(filtered_tag_counts.select("tag"), "tag", "inner")
    print(f"Assegnazioni totali di tag dopo aver filtrato i tag comuni: {tags_dataset_filtered.count()}")

    tags_dataset_agg = tags_dataset_filtered.groupBy(col("id").alias("id_ref_tags")).agg(collect_list("tag").alias("tags"))
    # tags_dataset_agg.printSchema()
    
    main_cols_expressions = [col("id").alias("_id")] + \
                            [tedx_dataset_main[c] for c in tedx_dataset_main.columns if c != "id"]
    
    tedx_dataset_main_renamed = tedx_dataset_main.select(main_cols_expressions)
    
    tedx_dataset_agg = tedx_dataset_main_renamed.join(
        tags_dataset_agg, 
        tedx_dataset_main_renamed["_id"] == tags_dataset_agg["id_ref_tags"],
        "left"
    ).drop("id_ref_tags")

    if "id" in tedx_dataset_agg.columns and "_id" in tedx_dataset_agg.columns and "id" != "_id":
         tedx_dataset_agg = tedx_dataset_agg.drop("id")

    # tedx_dataset_agg.printSchema()

    if 'tags' in tedx_dataset_agg.columns:
        tedx_dataset_agg = tedx_dataset_agg.withColumn("tags", coalesce(col("tags"), array().cast("array<string>")))
        
        exploded_tags = tedx_dataset_agg.select("_id", explode("tags").alias("tag"))

        t1 = exploded_tags.alias("t1")
        t2 = exploded_tags.alias("t2")

        common_tags_count_df = t1.join(t2, (col("t1.tag") == col("t2.tag")) & (col("t1._id") != col("t2._id")), "inner") \
                                    .groupBy(col("t1._id").alias("source_id"), col("t2._id").alias("related_id")) \
                                    .agg(count("*").alias("common_tags_count"))

        window_spec = Window.partitionBy("source_id").orderBy(col("common_tags_count").desc())
        ranked_related_talks = common_tags_count_df.withColumn("rank", rank().over(window_spec))
        top_5_related_talks = ranked_related_talks.filter(col("rank") <= 5)

        next_watch_mapping = top_5_related_talks \
            .orderBy("source_id", col("common_tags_count").desc(), "related_id") \
            .groupBy("source_id") \
            .agg(collect_list("related_id").alias("next_watch")) \
            .withColumnRenamed("source_id", "join_id")
        
        # next_watch_mapping.printSchema()

        tedx_final_dataset = tedx_dataset_agg.join(
            next_watch_mapping,
            tedx_dataset_agg["_id"] == next_watch_mapping["join_id"],
            "left"
        ).drop("join_id")

        array_type_string = ArrayType(StringType())
        
        tedx_final_dataset = tedx_final_dataset.withColumn(
            "next_watch",
            coalesce(col("next_watch"), lit(None).cast(array_type_string))
        )
        
        # tedx_final_dataset.printSchema()

    else: # Caso in cui 'tags' non è in tedx_dataset_agg
            print("Attenzione: colonna 'tags' non trovata dopo l'aggregazione. Salto il calcolo di next_watch.")
            tedx_final_dataset = tedx_dataset_agg.withColumn("next_watch", array().cast(ArrayType(StringType())))


else: # Caso in cui 'id' o 'tag' non sono in tags_dataset
    print("Attenzione: colonna 'id' o 'tag' non trovata in tags_dataset. Salto aggregazione tag e calcolo next_watch.")
    
    select_exprs_no_tags = [col("id").alias("_id")] + \
                           [tedx_dataset_main[c] for c in tedx_dataset_main.columns if c != "id"]
                           
    tedx_final_dataset = tedx_dataset_main \
        .select(select_exprs_no_tags) \
        .withColumn("tags", array().cast(ArrayType(StringType()))) \
        .withColumn("next_watch", array().cast(ArrayType(StringType())))
    
    if "id" in tedx_final_dataset.columns and "_id" in tedx_final_dataset.columns and "id" != "_id":
        tedx_final_dataset = tedx_final_dataset.drop("id")

# Gestione finale delle colonne prima della scrittura
if tedx_final_dataset is not None:
    # Assicurati che la colonna 'slug' esista e sia StringType
    if "slug" not in tedx_final_dataset.columns:
        print("Errore critico: colonna 'slug' mancante nel dataset finale. Lo script potrebbe non funzionare come previsto.")
        # Considera di terminare o aggiungere una colonna slug vuota se assolutamente necessario
        # tedx_final_dataset = tedx_final_dataset.withColumn("slug", lit(None).cast(StringType()))
    else:
         tedx_final_dataset = tedx_final_dataset.withColumn("slug", coalesce(col("slug"), lit(None).cast(StringType())))

    # Assicurati che la colonna 'transcript' esista e sia StringType
    if "transcript" not in tedx_final_dataset.columns:
        print("Attenzione: colonna 'transcript' mancante nel dataset finale. Aggiunta come colonna vuota.")
        tedx_final_dataset = tedx_final_dataset.withColumn("transcript", lit(None).cast(StringType()))
    else:
        tedx_final_dataset = tedx_final_dataset.withColumn("transcript", coalesce(col("transcript"), lit(None).cast(StringType())))
    
    # Assicurati che 'tags' e 'next_watch' esistano se non create prima
    if "tags" not in tedx_final_dataset.columns:
        tedx_final_dataset = tedx_final_dataset.withColumn("tags", array().cast(ArrayType(StringType())))
    if "next_watch" not in tedx_final_dataset.columns:
        tedx_final_dataset = tedx_final_dataset.withColumn("next_watch", array().cast(ArrayType(StringType())))


if tedx_final_dataset is not None: # Ricontrolla dopo le aggiunte potenziali
    print("Schema finale prima della scrittura su MongoDB:")
    tedx_final_dataset.printSchema() 
    
    final_count = tedx_final_dataset.count()
    print(f"Numero di record in tedx_final_dataset da scrivere: {final_count}")
    
    if final_count == 0:
        print("Attenzione: Il dataset finale è vuoto. Salto la scrittura su MongoDB.")
    else:
        write_mongo_options = {
            "connectionName": "TEDX", 
            "database": "unibg_tedx_2025",
            "collection": "tedx_data",
            "ssl": "true",
            "ssl.domain_match": "false"}

        tedx_dataset_dynamic_frame = DynamicFrame.fromDF(tedx_final_dataset, glueContext, "nested")

        print("Scrittura del dataset finale in MongoDB...")
        glueContext.write_dynamic_frame.from_options(
            frame=tedx_dataset_dynamic_frame,
            connection_type="mongodb",
            connection_options=write_mongo_options
        )
        print("Dati scritti con successo in MongoDB.")
else:
    print("Errore: Il dataset finale ('tedx_final_dataset') non è stato creato o è None a causa di errori precedenti. Salto la scrittura su MongoDB.")

job.commit()