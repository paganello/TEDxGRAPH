###### TEDx-Load-Aggregate-Model ######

import sys
import json
import pyspark
from pyspark.sql.functions import col, collect_list, array_join, explode, collect_set, lit, coalesce, array # <-- Added explode, collect_set, lit, coalesce, array

from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.dynamicframe import DynamicFrame
from awsglue.job import Job


##### FROM FILES
tedx_dataset_path = "s3://tedx-2025-data-hk/final_list.csv"

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
    tedx_dataset = tedx_dataset.filter(col("id").isNotNull()) #check if id is not null

else:
    print("Warning: 'id' column not found in tedx_dataset. Skipping null key check.")
    print(f"Number of items from RAW DATA {count_items}")


## READ THE DETAILS
details_dataset_path = "s3://tedx-2025-data-hk/details.csv"
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
tags_dataset_path = "s3://tedx-2025-data-hk/tags.csv"
tags_dataset = spark.read.option("header","true").csv(tags_dataset_path)

# Check if 'id' and 'tag' columns exist in tags_dataset
if 'id' in tags_dataset.columns and 'tag' in tags_dataset.columns:
    # CREATE THE AGGREGATE MODEL, ADD TAGS TO TEDX_DATASET
    tags_dataset_agg = tags_dataset.groupBy(col("id").alias("id_ref")).agg(collect_list("tag").alias("tags"))
    tags_dataset_agg.printSchema()

    # Ensure 'id' exists in tedx_dataset_main before joining tags
    if 'id' in tedx_dataset_main.columns:
        tedx_dataset_agg = tedx_dataset_main.join(tags_dataset_agg, tedx_dataset_main["id"] == tags_dataset_agg["id_ref"], "left") \
            .drop("id_ref") \
            .select(col("id").alias("_id"), col("*")) \
            .drop("id")
        tedx_dataset_agg.printSchema()

        # --------- START: Calculate next_watch ---------

        # 1. Explode tags: Create rows like (_id, tag)
        # Ensure 'tags' column exists and handle potential nulls before exploding
        if 'tags' in tedx_dataset_agg.columns:
            # Handle talks that might not have tags (due to left join earlier)
            tedx_dataset_agg = tedx_dataset_agg.withColumn("tags", coalesce(col("tags"), array().cast("array<string>")))
            exploded_tags = tedx_dataset_agg.select("_id", explode("tags").alias("tag"))

            # 2. Self-join on tag to find talks with common tags
            # Alias the exploded dataframe to perform self-join
            t1 = exploded_tags.alias("t1")
            t2 = exploded_tags.alias("t2")

            # Join where tags match AND the talk IDs are different
            related_pairs = t1.join(t2, (col("t1.tag") == col("t2.tag")) & (col("t1._id") != col("t2._id")), "inner") \
                              .select(col("t1._id").alias("source_id"), col("t2._id").alias("related_id")) \
                              .distinct() # Ensure unique pairs (source_id, related_id)

            # 3. Aggregate related IDs for each source ID
            # Use collect_set to get unique related IDs per source talk
            next_watch_mapping = related_pairs.groupBy("source_id") \
                                              .agg(collect_set("related_id").alias("next_watch")) \
                                              .withColumnRenamed("source_id", "join_id") # Rename to avoid clash

            next_watch_mapping.printSchema()

            # 4. Left join the next_watch mapping back to the main aggregated dataset
            tedx_final_dataset = tedx_dataset_agg.join(
                next_watch_mapping,
                tedx_dataset_agg["_id"] == next_watch_mapping["join_id"],
                "left"
            ).drop("join_id") # Drop the join key from the mapping table

            # 5. Handle talks with no related items (replace null next_watch with empty list)
            # Determine the type of _id for correct casting of empty list lit([])
            # Assuming _id is string based on typical CSV reads and usage. Adjust if it's numeric.
            id_type = dict(tedx_final_dataset.dtypes)['_id']
            if id_type.startswith("array"): # Should not happen for _id, but defensive check
               print(f"Warning: _id column has unexpected type {id_type}")
               # Fallback or error handling needed
            elif id_type in ("int", "bigint", "long", "short", "byte"):
                 array_type = "array<long>" # Or appropriate numeric type
            else: # Default to string
                 array_type = "array<string>"

            tedx_final_dataset = tedx_final_dataset.withColumn(
                "next_watch",
                coalesce(col("next_watch"), lit(None).cast(array_type)) # Use lit(None).cast for empty array
                # Alternative using array() but needs specific type: coalesce(col("next_watch"), array().cast(array_type))
            )

            tedx_final_dataset.printSchema()

            # --------- END: Calculate next_watch ---------

        else:
             print("Warning: 'tags' column not found after aggregation. Skipping next_watch calculation.")
             # Add an empty next_watch column if tags column was missing
             tedx_final_dataset = tedx_dataset_agg.withColumn("next_watch", array().cast("array<string>"))


    else:
        print("Error: 'id' column missing in tedx_dataset_main for joining tags. Exiting.")
        sys.exit(1) # Or handle error appropriately

else:
    print("Warning: 'id' or 'tag' column not found in tags_dataset. Skipping tags aggregation and next_watch calculation.")
    # Add empty tags and next_watch columns if tags couldn't be processed
    tedx_final_dataset = tedx_dataset_main.withColumn("tags", array().cast("array<string>")) \
                                         .withColumn("next_watch", array().cast("array<string>")) \
                                         .select(col("id").alias("_id"), col("*")) \
                                         .drop("id") # Ensure _id exists even if tags failed


# --- Writing to MongoDB ---
# Use the final dataset with the 'next_watch' column
if 'tedx_final_dataset' in locals():
    write_mongo_options = {
        "connectionName": "Mongodbatlas connection", # Make sure this connection is configured in Glue
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
    print("Error: Final dataset ('tedx_final_dataset') was not created due to previous errors. Skipping MongoDB write.")


job.commit()