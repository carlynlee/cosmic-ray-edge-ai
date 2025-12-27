# Kibana Dashboard Setup for CosmicWatch Data

## Overview

Kibana can replace the Python visualization dashboard with interactive, real-time visualizations. This is **recommended for SC25** as it's more impressive and easier to use during demonstrations.

## Advantages of Kibana Dashboard

✅ **Interactive:** Filter, zoom, and explore data in real-time  
✅ **Real-time updates:** Auto-refresh capabilities  
✅ **Multiple visualizations:** Create various chart types  
✅ **Public access:** Already available at https://credo-kibana.nrp-nautilus.io  
✅ **No Python script needed:** Everything runs in the browser  
✅ **Better for demos:** More professional and easier to explain  

## Quick Setup Guide

### 1. Access Kibana

Navigate to: **https://credo-kibana.nrp-nautilus.io**

Login:
- Username: `elastic`
- Password: (retrieve from Kubernetes secret)

### 2. Create Index Pattern (if not already done)

1. Go to **Stack Management** → **Index Patterns**
2. Click **Create index pattern**
3. Pattern: `credo-detections*`
4. Select **timestamp** as the time field
5. Click **Create index pattern**

### 3. Create Visualizations

#### A. Event Count Over Time

1. Go to **Visualize Library** → **Create visualization**
2. Choose **Line** chart
3. Select index pattern: `credo-detections*`
4. Configure:
   - **X-axis:** Date Histogram on `timestamp` (1 hour interval)
   - **Y-axis:** Count
   - **Filter:** `source: cosmicwatch-v3x`
5. Save as: "CosmicWatch Events Over Time"

#### B. Coincidence Rate Comparison

1. Create new **Line** chart
2. Configure:
   - **X-axis:** Date Histogram on `timestamp` (1 hour interval)
   - **Y-axis:** Average of `coincident` (as percentage)
   - **Add metric:** Average of `ml_prediction` (as percentage)
   - **Filter:** `source: cosmicwatch-v3x`
3. Save as: "Coincidence Rate Comparison"

#### C. Statistics Summary

1. Create **Metric** visualization
2. Add metrics:
   - Total Events: Count with filter `source: cosmicwatch-v3x`
   - Coincidence Events: Count with filter `source: cosmicwatch-v3x AND coincident: true`
   - Predicted Coincidence: Count with filter `source: cosmicwatch-v3x AND ml_prediction: 1`
3. Save as: "Event Statistics"

#### D. Model Accuracy

1. Create **Metric** visualization
2. Use **Painless script** aggregation:
   ```painless
   if (doc['coincident'].value == doc['ml_prediction'].value) {
       return 1;
   } else {
       return 0;
   }
   ```
3. Calculate average to get accuracy percentage
4. Filter: `source: cosmicwatch-v3x AND _exists_: ml_prediction`
5. Save as: "Model Accuracy"

### 4. Create Dashboard

1. Go to **Dashboards** → **Create dashboard**
2. Add saved visualizations:
   - CosmicWatch Events Over Time
   - Coincidence Rate Comparison
   - Event Statistics
   - Model Accuracy
3. Arrange and resize visualizations
4. Enable **Auto-refresh** (e.g., every 1 minute)
5. Save as: "CosmicWatch Real-Time Dashboard"

## Equivalent Visualizations

| Python Dashboard | Kibana Equivalent |
|------------------|-------------------|
| Event counts over time | Line chart: Date histogram on timestamp |
| Coincidence vs prediction rate | Line chart: Two metrics (avg coincident, avg ml_prediction) |
| Statistics summary | Metric visualization: Multiple count metrics |
| Model accuracy | Metric with scripted aggregation |

## Advanced Features

### Real-Time Filtering

Add filters to the dashboard:
- `source: cosmicwatch-v3x` - Only CosmicWatch data
- `coincident: true` - Only coincidence events
- `ml_prediction: 1` - Only predicted coincidences
- Time range selector - Last 24 hours, last week, etc.

### Additional Visualizations

**Energy Spectrum (ADC Distribution):**
- Histogram of `adc_value`
- Filter: `source: cosmicwatch-v3x`

**Coincidence vs Non-Coincidence Comparison:**
- Pie chart: Split by `coincident` field
- Filter: `source: cosmicwatch-v3x`

**Environmental Correlations:**
- Scatter plot: `pressure_pa` vs detection rate
- Line chart: `temperature_c` over time

**Prediction Confidence:**
- Histogram of `ml_probability`
- Filter: `source: cosmicwatch-v3x AND _exists_: ml_probability`

## For SC25 Demonstration

### Recommended Dashboard Layout

1. **Top Row:**
   - Event Statistics (metrics)
   - Model Accuracy (metric)

2. **Middle Row:**
   - Events Over Time (line chart, full width)

3. **Bottom Row:**
   - Coincidence Rate Comparison (line chart, full width)

### Auto-Refresh Settings

- **During demo:** 30 seconds or 1 minute
- **For presentation:** 5 minutes (less distracting)

### Time Range

- Set default to **Last 7 days** or **Last 30 days** (to include data with 2025 timestamps)
- Allow users to adjust with time picker

## Comparison: Python vs Kibana

| Feature | Python Dashboard | Kibana Dashboard |
|---------|------------------|------------------|
| Real-time updates | ✅ Yes (60s interval) | ✅ Yes (configurable) |
| Interactive | ❌ Static PNG | ✅ Fully interactive |
| Public access | ❌ Local file | ✅ Public URL |
| Multiple charts | ✅ 4 panels | ✅ Unlimited |
| Filtering | ❌ No | ✅ Yes |
| Zoom/Pan | ❌ No | ✅ Yes |
| Export | ✅ PNG only | ✅ PNG, PDF, CSV |
| Setup complexity | Medium | Low (once configured) |
| Best for demo | ⚠️ Static | ✅ **Interactive** |

## Recommendation

**Use Kibana Dashboard for SC25:**
- More impressive for demonstrations
- Easier to explain and interact with
- Already publicly accessible
- No need to run Python scripts during demo
- Can show real-time data updates

**Keep Python Dashboard as backup:**
- If Kibana is unavailable
- For offline analysis
- For generating static reports

## Quick Start Commands

```bash
# Access Kibana
open https://credo-kibana.nrp-nautilus.io

# Or verify data is accessible
curl -k -u "elastic:PASSWORD" "https://localhost:9200/credo-detections/_count" \
  -H "Content-Type: application/json" \
  -d '{"query": {"term": {"source": "cosmicwatch-v3x"}}}'
```

## Troubleshooting

**No data visible:**
- Check time range (data may have 2025 timestamps)
- Verify index pattern includes `credo-detections*`
- Add filter: `source: cosmicwatch-v3x`

**Visualizations not updating:**
- Enable auto-refresh in dashboard settings
- Check time range includes recent data

**ml_prediction field missing:**
- Ensure inference pipeline is running
- Check that documents have been processed

## Next Steps

1. **Create the visualizations** (15-30 minutes)
2. **Arrange in dashboard** (10 minutes)
3. **Test auto-refresh** (verify it works)
4. **Practice demo** (navigate and explain)
5. **Create backup static PNG** (from Python script, just in case)




