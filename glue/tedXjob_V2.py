###### TEDx-Load-Aggregate-Model ######

import sys
import json
# import pyspark # Non necessario se SparkContext è già importato
from pyspark.sql.functions import col, collect_list, array_join, explode, collect_set, lit, coalesce, array, count, slice, rank # <-- rank spostato qui
from pyspark.sql.window import Window # Aggiunto Window
from pyspark.sql.types import ArrayType, StringType # Aggiunto per cast più espliciti se necessario

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

#### READ INPUT FILES TO CREATE AN INPUT DATASET
tedx_dataset = spark.read \
    .option("header","true") \
    .option("quote", "\"") \
    .option("escape", "\"") \
    .csv(tedx_dataset_path)

tedx_dataset.printSchema()

#### FILTER ITEMS WITH NULL POSTING KEY
count_items = tedx_dataset.count()
if 'id' in tedx_dataset.columns:
    count_items_null = tedx_dataset.filter(col("id").isNotNull()).count()
    print(f"Number of items from RAW DATA {count_items}")
    print(f"Number of items from RAW DATA with NOT NULL KEY {count_items_null}")
    tedx_dataset = tedx_dataset.filter(col("id").isNotNull()) 

else:
    print("Warning: 'id' column not found in tedx_dataset. Skipping null key check.")
    print(f"Number of items from RAW DATA {count_items}")


## READ THE DETAILS
details_dataset_path = "s3://tedx-2025-data-mp-provaprova/details.csv"
details_dataset = spark.read \
    .option("header","true") \
    .option("quote", "\"") \
    .option("escape", "\"") \
    .csv(details_dataset_path)

details_dataset = details_dataset.select(col("id").alias("id_ref"),
                                             col("description"),
                                             col("duration"),
                                             col("publishedAt"))

# AND JOIN WITH THE MAIN TABLE
tedx_dataset_main = tedx_dataset.join(details_dataset, tedx_dataset["id"] == details_dataset["id_ref"], "left") \
            .drop("id_ref")

tedx_dataset_main.printSchema()


## READ TAGS DATASET
tags_dataset_path = "s3://tedx-2025-data-mp-provaprova/tags.csv"
tags_dataset = spark.read.option("header","true").csv(tags_dataset_path)

if 'id' in tags_dataset.columns and 'tag' in tags_dataset.columns:

    print("Filtering common tags...")
    tag_threshold = 500
    tag_counts = tags_dataset.groupBy("tag").agg(count("*").alias("tag_occurrence"))
    
    print(f"Total unique tags before filtering: {tag_counts.count()}")
    filtered_tag_counts = tag_counts.filter(col("tag_occurrence") <= tag_threshold)
    print(f"Total unique tags after filtering (<= {tag_threshold} occurrences): {filtered_tag_counts.count()}")

    tags_dataset_filtered = tags_dataset.join(filtered_tag_counts.select("tag"), "tag", "inner")
    print(f"Total tag assignments after filtering common tags: {tags_dataset_filtered.count()}")

    tags_dataset_agg = tags_dataset_filtered.groupBy(col("id").alias("id_ref")).agg(collect_list("tag").alias("tags"))
    tags_dataset_agg.printSchema()

    if 'id' in tedx_dataset_main.columns:
        tedx_dataset_agg = tedx_dataset_main.join(tags_dataset_agg, tedx_dataset_main["id"] == tags_dataset_agg["id_ref"], "left") \
            .drop("id_ref") \
            .select(col("id").alias("_id"), col("*")) \
            .drop("id")
        tedx_dataset_agg.printSchema()

        if 'tags' in tedx_dataset_agg.columns:
            tedx_dataset_agg = tedx_dataset_agg.withColumn("tags", coalesce(col("tags"), array().cast("array<string>")))
            
            exploded_tags = tedx_dataset_agg.select("_id", explode("tags").alias("tag"))

            t1 = exploded_tags.alias("t1")
            t2 = exploded_tags.alias("t2")

            common_tags_count_df = t1.join(t2, (col("t1.tag") == col("t2.tag")) & (col("t1._id") != col("t2._id")), "inner") \
                                     .groupBy(col("t1._id").alias("source_id"), col("t2._id").alias("related_id")) \
                                     .agg(count("*").alias("common_tags_count"))

            window_spec = Window.partitionBy("source_id").orderBy(col("common_tags_count").desc())
            
            # from pyspark.sql.functions import rank # <-- RIMOSSO DA QUI, SPOSTATO IN CIMA AL FILE
            ranked_related_talks = common_tags_count_df.withColumn("rank", rank().over(window_spec))

            top_5_related_talks = ranked_related_talks.filter(col("rank") <= 5)

            # !!! INIZIO SEZIONE CRITICA PER L'INDENTAZIONE !!!
            # Assicurati che le seguenti righe che iniziano con '.' abbiano ESATTAMENTE la stessa indentazione.
            # Solitamente sono indentate di 4 spazi rispetto alla riga 'next_watch_mapping = ...'
            next_watch_mapping = top_5_related_talks \
                .orderBy("source_id", col("common_tags_count").desc(), "related_id") \
                .groupBy("source_id") \
                .agg(collect_list("related_id").alias("next_watch")) \
                .withColumnRenamed("source_id", "join_id")
            # !!! FINE SEZIONE CRITICA PER L'INDENTAZIONE !!!

            next_watch_mapping.printSchema()

            tedx_final_dataset = tedx_dataset_agg.join(
                next_watch_mapping,
                tedx_dataset_agg["_id"] == next_watch_mapping["join_id"],
                "left"
            ).drop("join_id")

            array_type = ArrayType(StringType())
            
            tedx_final_dataset = tedx_final_dataset.withColumn(
                "next_watch",
                coalesce(col("next_watch"), lit(None).cast(array_type))
            )
            
            tedx_final_dataset.printSchema()

        else:
             print("Warning: 'tags' column not found after aggregation. Skipping next_watch calculation.")
             tedx_final_dataset = tedx_dataset_agg.withColumn("next_watch", array().cast(ArrayType(StringType())))

    else:
        print("Error: 'id' column missing in tedx_dataset_main for joining tags. Exiting.")
        tedx_final_dataset = None 
        job.commit() 
        sys.exit(1)

else:
    print("Warning: 'id' or 'tag' column not found in tags_dataset. Skipping tags aggregation and next_watch calculation.")
    tedx_final_dataset = tedx_dataset_main.withColumn("tags", array().cast(ArrayType(StringType()))) \
                                         .withColumn("next_watch", array().cast(ArrayType(StringType()))) \
                                         .select(col("id").alias("_id"), col("*")) \
                                         .drop("id")

if tedx_final_dataset is not None and 'tedx_final_dataset' in locals():
    write_mongo_options = {
        "connectionName": "TEDX", 
        "database": "unibg_tedx_2025",
        "collection": "tedx_data",
        "ssl": "true",
        "ssl.domain_match": "false"}

    tedx_dataset_dynamic_frame = DynamicFrame.fromDF(tedx_final_dataset, glueContext, "nested")

    print("Writing final dataset to MongoDB...")
    glueContext.write_dynamic_frame.from_options(
        frame=tedx_dataset_dynamic_frame,
        connection_type="mongodb",
        connection_options=write_mongo_options
    )
    print("Successfully wrote data to MongoDB.")
else:
    print("Error: Final dataset ('tedx_final_dataset') was not created or is None due to previous errors. Skipping MongoDB write.")

job.commit()