from pyspark.sql import *
from pyspark.sql import functions as F

# 1. Initialize the local big data compute engine
spark = SparkSession.builder \
    .appName("TokyoTransitBigDataPipeline") \
    .config("spark.sql.session.timeZone", "Asia/Tokyo") \
    .getOrCreate()

print("🌟 PySpark Cluster Active!")

# 2. Ingest data lake
df = spark.read.parquet("./*.parquet")

# 3. Transform the integer hour into an explicit timestamp string column
# lpad makes sure single digits look like '08' instead of '8'
formatted_df = df.withColumn(
    "timestamp_string",
    F.concat(
        F.lit("2026-01-01 "), 
        F.lpad(F.col("current_hour"), 2, "0"), 
        F.lit(":00:00")
    )
)

# 4. Sort chronologically by the new formatted time string
grouped_df = formatted_df.orderBy('timestamp_string')

# 5. Export back out as a single consolidated tracking file
grouped_df.coalesce(1) \
    .write \
    .mode("overwrite") \
    .option("header", "true") \
    .csv("./kepler_tokyo_transit")

print("🎉 Single CSV file exported successfully with Kepler time compliance!")