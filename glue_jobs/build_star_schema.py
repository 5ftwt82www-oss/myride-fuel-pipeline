"""
Glue job 2: Silver -> Gold
Builds a star schema (1 fact + 4 dimensions) and attaches the fuel price
that was in force on each trip date (point-in-time join).
"""
from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F

spark = SparkSession.builder.getOrCreate()
spark.conf.set("spark.sql.ansi.enabled", "false")
BUCKET = "s3://erlangga-myride-fuel-pipeline"

trips = spark.read.parquet(f"{BUCKET}/clean/trips/")
fuel = spark.read.parquet(f"{BUCKET}/clean/fuel/")


# Helper: list each unique value once and give it a number ID
def build_dim(df, cols, id_name):
    w = Window.orderBy(*cols)
    return df.select(*cols).distinct().withColumn(id_name, F.row_number().over(w))


# ---------- DIMENSION TABLES ----------
areas = (trips.select(F.col("pickup_area").alias("area"), "state")
         .union(trips.select(F.col("dropoff_area").alias("area"), "state")))
dim_area = build_dim(areas, ["area", "state"], "area_id")
dim_service = build_dim(trips, ["service_type"], "service_id")
dim_payment = build_dim(trips, ["payment_method"], "payment_id")

dim_date = trips.select("trip_date").distinct().select(
    F.date_format("trip_date", "yyyyMMdd").cast("int").alias("date_key"),
    F.col("trip_date").alias("date"),
    F.year("trip_date").alias("year"),
    F.month("trip_date").alias("month"),
    F.date_format("trip_date", "EEEE").alias("day_name"),
    F.dayofweek("trip_date").isin(1, 7).alias("is_weekend"))

# ---------- MATCH EACH DAY TO THAT WEEK'S FUEL PRICE ----------
days = trips.select("trip_date").distinct()
latest = Window.partitionBy("trip_date").orderBy(F.desc("price_date"))
fuel_daily = (days.join(fuel, fuel.price_date <= days.trip_date)
    .withColumn("rn", F.row_number().over(latest))
    .filter("rn = 1")
    .select("trip_date", "ron95", "diesel"))

# ---------- FACT TABLE ----------
pickup = dim_area.withColumnRenamed("area", "pickup_area").withColumnRenamed("area_id", "pickup_area_id")
dropoff = dim_area.withColumnRenamed("area", "dropoff_area").withColumnRenamed("area_id", "dropoff_area_id")

fact_trips = (trips
    .join(pickup, ["pickup_area", "state"])
    .join(dropoff, ["dropoff_area", "state"])
    .join(dim_service, "service_type")
    .join(dim_payment, "payment_method")
    .join(fuel_daily, "trip_date", "left")
    .select("trip_id",
            F.date_format("trip_date", "yyyyMMdd").cast("int").alias("date_key"),
            F.hour("trip_datetime").alias("trip_hour"),
            "pickup_area_id", "dropoff_area_id", "service_id", "payment_id",
            "distance_km", "surge_multiplier", "fare",
            F.round(F.col("fare") / F.col("distance_km"), 2).alias("fare_per_km"),
            "rating",
            F.col("ron95").alias("ron95_price"),
            F.col("diesel").alias("diesel_price")))

# ---------- SAVE TO GOLD ----------
tables = {"fact_trips": fact_trips, "dim_area": dim_area, "dim_service": dim_service,
          "dim_payment": dim_payment, "dim_date": dim_date}
for name, df in tables.items():
    df.write.mode("overwrite").parquet(f"{BUCKET}/gold/{name}/")
