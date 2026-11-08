"""
Glue job 1: Bronze -> Silver
Cleans raw trips and fuel prices and writes them to S3 as Parquet.
"""
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

spark = SparkSession.builder.getOrCreate()
spark.conf.set("spark.sql.legacy.timeParserPolicy", "CORRECTED")
# ANSI mode makes to_timestamp throw on a non-matching format; disable it so
# the second date format can be tried via coalesce().
spark.conf.set("spark.sql.ansi.enabled", "false")
BUCKET = "s3://erlangga-myride-fuel-pipeline"

# ---------- TRIPS ----------
trips = spark.read.option("header", True).csv(f"{BUCKET}/raw/trips/")

# 1. Remove exact duplicate rows
trips = trips.dropDuplicates()

# 2. Fix typos in place names
fixes = {"p. jaya": "Petaling Jaya", "petaling jaya": "Petaling Jaya", "pj": "Petaling Jaya",
         "jb": "Johor Bahru", "johor bahru": "Johor Bahru", "johor baru": "Johor Bahru",
         "kl": "Kuala Lumpur", "kuala lumpur": "Kuala Lumpur",
         "shah alam": "Shah Alam", "shahalam": "Shah Alam"}
mapping = F.create_map([F.lit(x) for kv in fixes.items() for x in kv])
for c in ["state", "pickup_area", "dropoff_area"]:
    key = F.lower(F.trim(F.col(c)))
    trips = trips.withColumn(c, F.coalesce(mapping[key], F.trim(F.col(c))))

# 3. Handle the two date formats
trips = trips.withColumn("trip_datetime", F.coalesce(
    F.to_timestamp("trip_datetime", "yyyy-MM-dd HH:mm:ss"),
    F.to_timestamp("trip_datetime", "dd/MM/yyyy HH:mm")))

# 4. Strip "RM" from fares and convert numbers
trips = (trips
    .withColumn("fare", F.regexp_replace("fare", "RM", "").cast("double"))
    .withColumn("distance_km", F.col("distance_km").cast("double"))
    .withColumn("surge_multiplier", F.col("surge_multiplier").cast("double"))
    .withColumn("rating", F.col("rating").cast("int")))

# 5. Drop bad rows: missing fare/date, or impossible distance
trips = trips.filter(F.col("fare").isNotNull() & F.col("trip_datetime").isNotNull() & (F.col("distance_km") > 0))
trips = trips.withColumn("trip_date", F.to_date("trip_datetime"))

trips.write.mode("overwrite").parquet(f"{BUCKET}/clean/trips/")

# ---------- FUEL ----------
fuel = spark.read.option("header", True).csv(f"{BUCKET}/raw/fuel/")
fuel = (fuel.filter(F.col("series_type") == "level")
    .select(F.to_date("date").alias("price_date"),
            F.col("ron95").cast("double"),
            F.col("ron97").cast("double"),
            F.col("diesel").cast("double")))
fuel.write.mode("overwrite").parquet(f"{BUCKET}/clean/fuel/")
