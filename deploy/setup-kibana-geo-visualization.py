#!/usr/bin/env python3
"""
Kibana Geographic Visualization Setup
Creates index pattern and sample visualizations for CREDO device locations
"""

import requests
import json
import time

# Kibana configuration
KIBANA_HOST = "http://localhost:5601"
KIBANA_USER = "elastic"
KIBANA_PASS = "<YOUR_ES_PASSWORD>"

class KibanaGeoVisualization:
    def __init__(self):
        self.session = requests.Session()
        self.session.auth = (KIBANA_USER, KIBANA_PASS)
        self.session.headers.update({'Content-Type': 'application/json', 'kbn-xsrf': 'true'})
        
    def wait_for_kibana(self):
        """Wait for Kibana to be ready"""
        print("⏳ Waiting for Kibana to be ready...")
        max_retries = 30
        for i in range(max_retries):
            try:
                response = self.session.get(f"{KIBANA_HOST}/api/status", timeout=5)
                if response.status_code == 200:
                    print("✅ Kibana is ready!")
                    return True
            except:
                pass
            time.sleep(2)
            print(f"   Attempt {i+1}/{max_retries}...")
        
        print("❌ Kibana is not responding")
        return False
    
    def create_index_pattern(self):
        """Create index pattern for credo-detections"""
        print("📊 Creating index pattern for credo-detections...")
        
        index_pattern = {
            "attributes": {
                "title": "credo-detections*",
                "timeFieldName": "timestamp"
            }
        }
        
        try:
            response = self.session.post(
                f"{KIBANA_HOST}/api/saved_objects/index-pattern/credo-detections",
                json=index_pattern,
                timeout=30
            )
            
            if response.status_code == 200:
                print("✅ Index pattern created successfully!")
                return True
            else:
                print(f"⚠️  Index pattern may already exist (status: {response.status_code})")
                return True
        except Exception as e:
            print(f"❌ Error creating index pattern: {e}")
            return False
    
    def create_geo_map_visualization(self):
        """Create a geographic map visualization"""
        print("🗺️  Creating geographic map visualization...")
        
        # Create a map visualization
        map_visualization = {
            "attributes": {
                "title": "CREDO Device Locations",
                "visState": json.dumps({
                    "title": "CREDO Device Locations",
                    "type": "tile_map",
                    "params": {
                        "mapType": "Scaled Circle Markers",
                        "isDesaturated": False,
                        "addTooltip": True,
                        "heatClusterSize": 1.5,
                        "legendPosition": "bottomright",
                        "mapZoom": 2,
                        "mapCenter": [18.0, 53.0]
                    },
                    "aggs": [
                        {
                            "id": "1",
                            "type": "count",
                            "schema": "metric",
                            "params": {}
                        },
                        {
                            "id": "2",
                            "type": "geohash_grid",
                            "schema": "segment",
                            "params": {
                                "field": "location",
                                "autoPrecision": True,
                                "precision": 2,
                                "useGeocentroid": True
                            }
                        }
                    ]
                }),
                "uiStateJSON": json.dumps({
                    "map": {
                        "center": [18.0, 53.0],
                        "zoom": 6
                    }
                }),
                "description": "Geographic distribution of CREDO cosmic ray detection devices",
                "version": 1,
                "kibanaSavedObjectMeta": {
                    "searchSourceJSON": json.dumps({
                        "index": "credo-detections",
                        "query": {
                            "match_all": {}
                        },
                        "filter": []
                    })
                }
            }
        }
        
        try:
            response = self.session.post(
                f"{KIBANA_HOST}/api/saved_objects/visualization/credo-device-locations",
                json=map_visualization,
                timeout=30
            )
            
            if response.status_code == 200:
                print("✅ Geographic map visualization created!")
                return True
            else:
                print(f"⚠️  Visualization may already exist (status: {response.status_code})")
                return True
        except Exception as e:
            print(f"❌ Error creating map visualization: {e}")
            return False
    
    def create_device_distribution_dashboard(self):
        """Create a dashboard with device distribution visualizations"""
        print("📈 Creating device distribution dashboard...")
        
        dashboard = {
            "attributes": {
                "title": "CREDO Device Distribution Dashboard",
                "description": "Comprehensive view of CREDO cosmic ray detection data distribution",
                "panelsJSON": json.dumps([
                    {
                        "version": "7.15.0",
                        "type": "visualization",
                        "gridData": {
                            "x": 0,
                            "y": 0,
                            "w": 24,
                            "h": 15,
                            "i": "1"
                        },
                        "panelIndex": "1",
                        "embeddableConfig": {},
                        "panelRefName": "panel_1"
                    }
                ]),
                "optionsJSON": json.dumps({
                    "useMargins": True,
                    "syncColors": False,
                    "hidePanelTitles": False
                }),
                "version": 1,
                "timeRestore": False,
                "kibanaSavedObjectMeta": {
                    "searchSourceJSON": json.dumps({
                        "query": {
                            "match_all": {}
                        },
                        "filter": []
                    })
                }
            }
        }
        
        try:
            response = self.session.post(
                f"{KIBANA_HOST}/api/saved_objects/dashboard/credo-device-dashboard",
                json=dashboard,
                timeout=30
            )
            
            if response.status_code == 200:
                print("✅ Device distribution dashboard created!")
                return True
            else:
                print(f"⚠️  Dashboard may already exist (status: {response.status_code})")
                return True
        except Exception as e:
            print(f"❌ Error creating dashboard: {e}")
            return False
    
    def print_instructions(self):
        """Print instructions for accessing Kibana visualizations"""
        print("\n" + "="*60)
        print("🎯 KIBANA GEOGRAPHIC VISUALIZATION SETUP COMPLETE!")
        print("="*60)
        
        print("\n📋 Access Instructions:")
        print("1. Open your browser and go to: http://localhost:5601")
        print("2. Login with:")
        print("   Username: elastic")
        print("   Password: <YOUR_ES_PASSWORD>")
        
        print("\n🗺️  Geographic Visualizations:")
        print("1. Go to 'Visualize' in the left sidebar")
        print("2. Look for 'CREDO Device Locations' map visualization")
        print("3. Or create a new 'Coordinate Map' visualization:")
        print("   - Select 'credo-detections' index pattern")
        print("   - Choose 'location' as the geospatial field")
        print("   - Add 'Count' metric aggregation")
        print("   - Add 'Geohash Grid' bucket aggregation")
        
        print("\n📊 Device Distribution Analysis:")
        print("1. Go to 'Discover' to explore the data")
        print("2. Create visualizations for:")
        print("   - Device ID distribution (Pie Chart)")
        print("   - User ID distribution (Bar Chart)")
        print("   - Time series of detections (Line Chart)")
        print("   - Geographic heat map (Coordinate Map)")
        
        print("\n🔍 Sample Queries:")
        print("- Filter by device: device_id:13")
        print("- Filter by location: location: [53.65, 18.72]")
        print("- Filter by time range: timestamp:[2017-01-01 TO 2018-12-31]")
        
        print("\n💡 Tips:")
        print("- Use 'Geohash Grid' for geographic clustering")
        print("- Use 'Terms' aggregation for device/user distribution")
        print("- Use 'Date Histogram' for time-based analysis")
        print("- Create dashboards to combine multiple visualizations")
        
        print("\n🚀 Ready to explore your CREDO data geographically!")
    
    def run_setup(self):
        """Run the complete Kibana setup"""
        print("🔧 Setting up Kibana Geographic Visualizations...")
        
        if not self.wait_for_kibana():
            return False
        
        self.create_index_pattern()
        self.create_geo_map_visualization()
        self.create_device_distribution_dashboard()
        
        self.print_instructions()
        return True

def main():
    setup = KibanaGeoVisualization()
    setup.run_setup()

if __name__ == "__main__":
    main()
