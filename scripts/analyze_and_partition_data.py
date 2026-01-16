#!/usr/bin/env python3
"""
Analyze and Partition CosmicWatch Data

This script analyzes CosmicWatch data and partitions it for federated learning:
- Node 1: Coincidence events (high-energy particles)
- Node 2: Non-coincidence events (single-detector)
- Node 3: CREDO.science data (historical)
"""

import json
import os
import sys
from collections import defaultdict
import statistics

def load_data(filename):
    """Load data from JSON file"""
    with open(filename, 'r') as f:
        return json.load(f)

def analyze_data(documents):
    """Analyze data distributions"""
    print("=== Data Analysis ===\n")
    
    # Basic counts
    total = len(documents)
    coincident = [d for d in documents if d.get('coincident') == True]
    non_coincident = [d for d in documents if d.get('coincident') == False]
    
    print(f"Total documents: {total:,}")
    print(f"Coincidence events: {len(coincident):,} ({len(coincident)/total*100:.1f}%)")
    print(f"Non-coincidence events: {len(non_coincident):,} ({len(non_coincident)/total*100:.1f}%)")
    
    # ADC analysis
    print("\n=== ADC Value Analysis ===")
    coincident_adc = [d.get('adc_value') for d in coincident if d.get('adc_value') is not None]
    non_coincident_adc = [d.get('adc_value') for d in non_coincident if d.get('adc_value') is not None]
    
    if coincident_adc:
        print(f"Coincidence events ADC:")
        print(f"  Min: {min(coincident_adc)}")
        print(f"  Max: {max(coincident_adc)}")
        print(f"  Avg: {sum(coincident_adc)/len(coincident_adc):.1f}")
        print(f"  Median: {statistics.median(coincident_adc):.1f}")
    
    if non_coincident_adc:
        print(f"Non-coincidence events ADC:")
        print(f"  Min: {min(non_coincident_adc)}")
        print(f"  Max: {max(non_coincident_adc)}")
        print(f"  Avg: {sum(non_coincident_adc)/len(non_coincident_adc):.1f}")
        print(f"  Median: {statistics.median(non_coincident_adc):.1f}")
    
    # SiPM analysis
    print("\n=== SiPM Voltage Analysis ===")
    coincident_sipm = [d.get('sipm_mv') for d in coincident if d.get('sipm_mv') is not None]
    non_coincident_sipm = [d.get('sipm_mv') for d in non_coincident if d.get('sipm_mv') is not None]
    
    if coincident_sipm:
        print(f"Coincidence events SiPM:")
        print(f"  Min: {min(coincident_sipm):.1f}")
        print(f"  Max: {max(coincident_sipm):.1f}")
        print(f"  Avg: {sum(coincident_sipm)/len(coincident_sipm):.1f}")
    
    if non_coincident_sipm:
        print(f"Non-coincidence events SiPM:")
        print(f"  Min: {min(non_coincident_sipm):.1f}")
        print(f"  Max: {max(non_coincident_sipm):.1f}")
        print(f"  Avg: {sum(non_coincident_sipm)/len(non_coincident_sipm):.1f}")
    
    # Environmental sensors
    print("\n=== Environmental Sensor Analysis ===")
    temps = [d.get('temperature_c') for d in documents if d.get('temperature_c') is not None]
    pressures = [d.get('pressure_pa') for d in documents if d.get('pressure_pa') is not None]
    
    if temps:
        print(f"Temperature: min={min(temps):.1f}°C, max={max(temps):.1f}°C, avg={sum(temps)/len(temps):.1f}°C")
    if pressures:
        print(f"Pressure: min={min(pressures):.0f}Pa, max={max(pressures):.0f}Pa, avg={sum(pressures)/len(pressures):.0f}Pa")
    
    # Missing data analysis
    print("\n=== Data Completeness ===")
    fields = ['adc_value', 'sipm_mv', 'coincident', 'temperature_c', 'pressure_pa', 
              'accel_x_g', 'accel_y_g', 'accel_z_g', 'gyro_x_degs', 'gyro_y_degs', 'gyro_z_degs']
    for field in fields:
        missing = sum(1 for d in documents if d.get(field) is None)
        print(f"{field}: {missing:,} missing ({missing/total*100:.1f}%)")
    
    return {
        'total': total,
        'coincident': len(coincident),
        'non_coincident': len(non_coincident),
        'coincident_adc_avg': sum(coincident_adc)/len(coincident_adc) if coincident_adc else None,
        'non_coincident_adc_avg': sum(non_coincident_adc)/len(non_coincident_adc) if non_coincident_adc else None,
    }

def partition_data(documents):
    """Partition data for federated learning"""
    print("\n=== Partitioning Data ===\n")
    
    # Node 1: Coincidence events
    node1 = [d for d in documents if d.get('coincident') == True]
    
    # Node 2: Non-coincidence events
    node2 = [d for d in documents if d.get('coincident') == False]
    
    print(f"Node 1 (Coincidence events): {len(node1):,} documents")
    print(f"Node 2 (Non-coincidence events): {len(node2):,} documents")
    
    # Save partitions
    os.makedirs('data/data_partitions', exist_ok=True)
    
    with open('data/data_partitions/node1_coincidence_events.json', 'w') as f:
        json.dump(node1, f, indent=2)
    print(f"✓ Saved Node 1 data to: data/data_partitions/node1_coincidence_events.json")
    
    with open('data/data_partitions/node2_non_coincidence_events.json', 'w') as f:
        json.dump(node2, f, indent=2)
    print(f"✓ Saved Node 2 data to: data/data_partitions/node2_non_coincidence_events.json")
    
    # Create training-ready datasets (CSV format)
    print("\n=== Creating Training Datasets ===")
    
    def create_csv(data, filename):
        """Create CSV file for training"""
        import csv
        
        # Define features
        features = ['adc_value', 'sipm_mv', 'temperature_c', 'pressure_pa',
                   'accel_x_g', 'accel_y_g', 'accel_z_g',
                   'gyro_x_degs', 'gyro_y_degs', 'gyro_z_degs']
        
        # Create label: energy level based on ADC
        # Low: ADC < 200, Medium: 200-500, High: > 500 OR coincidence
        def get_energy_level(doc):
            adc = doc.get('adc_value', 0)
            is_coincident = doc.get('coincident', False)
            
            if is_coincident or adc > 500:
                return 'high'
            elif adc >= 200:
                return 'medium'
            else:
                return 'low'
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            # Header
            writer.writerow(features + ['energy_level', 'coincident'])
            
            # Data rows
            for doc in data:
                row = [doc.get(f, '') for f in features]
                row.append(get_energy_level(doc))
                row.append(1 if doc.get('coincident') else 0)
                writer.writerow(row)
    
    create_csv(node1, 'data/data_partitions/node1_coincidence_events.csv')
    print(f"✓ Created CSV: data/data_partitions/node1_coincidence_events.csv")
    
    create_csv(node2, 'data/data_partitions/node2_non_coincidence_events.csv')
    print(f"✓ Created CSV: data/data_partitions/node2_non_coincidence_events.csv")
    
    # Summary
    print(f"\n=== Partition Summary ===")
    print(f"Node 1 (Coincidence): {len(node1):,} events")
    print(f"Node 2 (Non-coincidence): {len(node2):,} events")
    print(f"Total: {len(documents):,} events")
    
    return node1, node2

def main():
    input_file = 'data/cosmicwatch_data_export.json'
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found")
        print("Please run export_cosmicwatch_data.py first")
        sys.exit(1)
    
    print(f"Loading data from {input_file}...")
    documents = load_data(input_file)
    print(f"Loaded {len(documents):,} documents\n")
    
    # Analyze data
    stats = analyze_data(documents)
    
    # Partition data
    node1, node2 = partition_data(documents)
    
    print("\n✓ Analysis and partitioning complete!")
    print("\nNext steps:")
    print("  1. Review data_partitions/ directory")
    print("  2. Use CSV files for model training")
    print("  3. Proceed to Day 3-4: Baseline Model Development")

if __name__ == "__main__":
    main()

