import arcpy
arcpy.env.overwriteOutput = True

# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# STEP 0) SETTINGS (EDIT THESE ONLY)
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
gdb = r"C:\Users\AHMAD\Documents\ArcGIS\Projects\MyProject3\MyProject3.gdb"
arcpy.env.workspace = gdb

pois_fc = "gis_osm_pois_free_1"  # POI points inside this GDB

# Islamabad center (lon, lat) and buffer distance
isb_lon, isb_lat = 73.0479, 33.6844
buffer_dist = "15000 Meters"  # change to 10000 or 20000 if you want

# Output names
sel_fc   = "POI_Health_Fire_SEL"
isb_center = "Islamabad_Center_Point"
isb_buffer = "Islamabad_Buffer_Polygon"
clip_fc  = "POI_Health_Fire_Isb_CLIP"
proj_fc  = "POI_Health_Fire_Isb_UTM43N"
health_fc = "Health_UTM"
fire_fc   = "Fire_UTM"
stats_tbl = "NearDist_Stats"

# CRS (meters)
out_sr = arcpy.SpatialReference(32643)  # WGS 1984 UTM Zone 43N

print("Workspace:", arcpy.env.workspace)

# Helper: safely delete outputs

def safe_delete(name):
    if arcpy.Exists(name):
        arcpy.management.Delete(name)
        print("Deleted:", name)

# Clean old outputs (optional work)
for o in [sel_fc, isb_center, isb_buffer, clip_fc, proj_fc, health_fc, fire_fc, stats_tbl]:
    safe_delete(o)

# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# STEP 1) Select healthcare + fire stations
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
where_clause = "fclass IN ('hospital','clinic','pharmacy','fire_station')"
arcpy.management.MakeFeatureLayer(pois_fc, "pois_lyr")
arcpy.management.SelectLayerByAttribute("pois_lyr", "NEW_SELECTION", where_clause)
arcpy.management.CopyFeatures("pois_lyr", sel_fc)
print("Step 1 OK | Selected count:", int(arcpy.management.GetCount(sel_fc)[0]))



# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# STEP 2) Create Islamabad center point (WGS84)
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
arcpy.management.CreateFeatureclass(gdb, isb_center, "POINT", spatial_reference=arcpy.SpatialReference(4326))
with arcpy.da.InsertCursor(isb_center, ["SHAPE@XY"]) as cur:
    cur.insertRow([(isb_lon, isb_lat)])
print("Step 2 OK | Islamabad center point created.")




# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# STEP 3) Buffer center point to create Islamabad study polygon
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
arcpy.analysis.Buffer(isb_center, isb_buffer, buffer_dist)
print("Step 3 OK | Islamabad buffer polygon created.")




# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# STEP 4) Clip selected POIs to Islamabad polygon
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
arcpy.analysis.Clip(sel_fc, isb_buffer, clip_fc)
clip_count = int(arcpy.management.GetCount(clip_fc)[0])
print("Step 4 OK | Clipped count:", clip_count)




# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# STEP 5) Project clipped points to UTM (meters)
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
arcpy.management.Project(clip_fc, proj_fc, out_sr)
proj_count = int(arcpy.management.GetCount(proj_fc)[0])
unit = arcpy.Describe(proj_fc).spatialReference.linearUnitName
print("Step 5 OK | Projected count:", proj_count, "| Unit:", unit)



# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# STEP 6) Split into healthcare vs fire stations
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
arcpy.management.MakeFeatureLayer(proj_fc, "health_lyr", "fclass <> 'fire_station'")
arcpy.management.CopyFeatures("health_lyr", health_fc)

arcpy.management.MakeFeatureLayer(proj_fc, "fire_lyr", "fclass = 'fire_station'")
arcpy.management.CopyFeatures("fire_lyr", fire_fc)

health_count = int(arcpy.management.GetCount(health_fc)[0])
fire_count = int(arcpy.management.GetCount(fire_fc)[0])
print("Step 6 OK | Healthcare:", health_count, "| Fire stations:", fire_count)

if fire_count == 0:
    raise RuntimeError("No fire_station features found inside the study area. Increase buffer_dist or verify POI data.")




# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# STEP 7) Near: healthcare -> nearest fire station + Statistics table
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
arcpy.analysis.Near(health_fc, fire_fc)
print("Step 7A OK | Near complete. NEAR_DIST added to:", health_fc)

arcpy.analysis.Statistics(
    in_table=health_fc,
    out_table=stats_tbl,
    statistics_fields=[
        ["NEAR_DIST", "MIN"],
        ["NEAR_DIST", "MAX"],
        ["NEAR_DIST", "MEAN"],
        ["NEAR_DIST", "STD"],
        ["NEAR_DIST", "MEDIAN"]
    ]
)
print("Step 7B OK | Stats table created:", stats_tbl)

print("\nALL DONE ✅ Outputs:")
print(" -", sel_fc)
print(" -", isb_center)
print(" -", isb_buffer)
print(" -", clip_fc)
print(" -", proj_fc)
print(" -", health_fc)
print(" -", fire_fc)
print(" -", stats_tbl)