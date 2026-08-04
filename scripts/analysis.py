#!/usr/bin/env python3
"""
Scientific Analysis of CosmicWatch Data

This script performs scientific analysis on CosmicWatch data:
- Energy spectrum visualization (ADC histograms)
- Coincidence rate analysis
- Environmental correlations (pressure, temperature)
- Temporal patterns (detection rate over time)
"""

import json
import os
import sys
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from collections import defaultdict
import statistics

def load_data(filename):
    """Load data from JSON file"""
    if not os.path.exists(filename):
        print(f"Error: {filename} not found")
        return None
    with open(filename, 'r') as f:
        return json.load(f)

def analyze_energy_spectrum(documents, output_dir):
    """Analyze and visualize energy spectrum (ADC distributions)"""
    print("\n=== Energy Spectrum Analysis ===")
    
    coincident = [d for d in documents if d.get('coincident') == True]
    non_coincident = [d for d in documents if d.get('coincident') == False]
    
    coincident_adc = [d.get('adc_value') for d in coincident if d.get('adc_value') is not None]
    non_coincident_adc = [d.get('adc_value') for d in non_coincident if d.get('adc_value') is not None]
    all_adc = coincident_adc + non_coincident_adc
    
    print(f"Total events: {len(all_adc):,}")
    print(f"Coincidence events: {len(coincident_adc):,} ({len(coincident_adc)/len(all_adc)*100:.1f}%)")
    print(f"Non-coincidence events: {len(non_coincident_adc):,} ({len(non_coincident_adc)/len(all_adc)*100:.1f}%)")
    
    if coincident_adc:
        print(f"\nCoincidence ADC Statistics:")
        print(f"  Min: {min(coincident_adc)}")
        print(f"  Max: {max(coincident_adc)}")
        print(f"  Mean: {np.mean(coincident_adc):.1f}")
        print(f"  Median: {np.median(coincident_adc):.1f}")
        print(f"  Std Dev: {np.std(coincident_adc):.1f}")
    
    if non_coincident_adc:
        print(f"\nNon-coincidence ADC Statistics:")
        print(f"  Min: {min(non_coincident_adc)}")
        print(f"  Max: {max(non_coincident_adc)}")
        print(f"  Mean: {np.mean(non_coincident_adc):.1f}")
        print(f"  Median: {np.median(non_coincident_adc):.1f}")
        print(f"  Std Dev: {np.std(non_coincident_adc):.1f}")
    
    # Create histogram
    plt.figure(figsize=(12, 6))
    
    plt.subplot(1, 2, 1)
    plt.hist(all_adc, bins=50, alpha=0.7, label='All Events', color='blue', edgecolor='black')
    plt.xlabel('ADC Value (Energy Proxy)')
    plt.ylabel('Count')
    plt.title('Energy Spectrum: All Events')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    plt.subplot(1, 2, 2)
    plt.hist(coincident_adc, bins=30, alpha=0.7, label='Coincidence', color='red', edgecolor='black')
    plt.hist(non_coincident_adc, bins=30, alpha=0.7, label='Non-coincidence', color='green', edgecolor='black')
    plt.xlabel('ADC Value (Energy Proxy)')
    plt.ylabel('Count')
    plt.title('Energy Spectrum: Coincidence vs Non-coincidence')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    plt.tight_layout()
    output_file = os.path.join(output_dir, 'energy_spectrum.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n✓ Saved energy spectrum plot: {output_file}")
    plt.close()
    
    return {
        'total_events': len(all_adc),
        'coincidence_count': len(coincident_adc),
        'coincidence_rate': len(coincident_adc)/len(all_adc)*100 if all_adc else 0,
        'coincidence_adc_mean': np.mean(coincident_adc) if coincident_adc else 0,
        'non_coincidence_adc_mean': np.mean(non_coincident_adc) if non_coincident_adc else 0,
        'adc_range': (min(all_adc), max(all_adc)) if all_adc else (0, 0)
    }

def analyze_coincidence_rate(documents):
    """Analyze coincidence rate and compare to theoretical expectations"""
    print("\n=== Coincidence Rate Analysis ===")
    
    total = len(documents)
    coincident = [d for d in documents if d.get('coincident') == True]
    coincidence_rate = len(coincident) / total * 100 if total > 0 else 0
    
    print(f"Total events: {total:,}")
    print(f"Coincidence events: {len(coincident):,}")
    print(f"Observed coincidence rate: {coincidence_rate:.2f}%")
    
    # Theoretical expectation: For two stacked detectors with separation d,
    # coincidence rate depends on muon flux, detector area, and geometry
    # Typical values: 5-15% for stacked detectors with ~10cm separation
    theoretical_range = (5, 15)
    print(f"\nTheoretical coincidence rate range: {theoretical_range[0]}-{theoretical_range[1]}%")
    
    if theoretical_range[0] <= coincidence_rate <= theoretical_range[1]:
        print(f"✓ Observed rate ({coincidence_rate:.2f}%) is within theoretical range")
    else:
        print(f"⚠ Observed rate ({coincidence_rate:.2f}%) is outside theoretical range")
        print("  (This may be due to detector geometry, muon flux, or environmental factors)")
    
    return {
        'observed_rate': coincidence_rate,
        'theoretical_range': theoretical_range,
        'within_range': theoretical_range[0] <= coincidence_rate <= theoretical_range[1]
    }

def analyze_environmental_correlations(documents, output_dir):
    """Analyze environmental correlations (pressure, temperature)"""
    print("\n=== Environmental Correlation Analysis ===")
    
    # Extract data with valid environmental sensors
    data_points = []
    for d in documents:
        if d.get('pressure_pa') is not None and d.get('temperature_c') is not None:
            data_points.append({
                'pressure': d.get('pressure_pa'),
                'temperature': d.get('temperature_c'),
                'sipm': d.get('sipm_mv'),
                'adc': d.get('adc_value'),
                'coincident': d.get('coincident', False)
            })
    
    if not data_points:
        print("⚠ No environmental sensor data available")
        return None
    
    print(f"Data points with environmental sensors: {len(data_points):,}")
    
    pressures = [d['pressure'] for d in data_points]
    temperatures = [d['temperature'] for d in data_points]
    sipm_voltages = [d['sipm'] for d in data_points if d['sipm'] is not None]
    
    print(f"\nPressure Statistics:")
    print(f"  Min: {min(pressures):.1f} Pa")
    print(f"  Max: {max(pressures):.1f} Pa")
    print(f"  Mean: {np.mean(pressures):.1f} Pa")
    print(f"  Std Dev: {np.std(pressures):.1f} Pa")
    
    print(f"\nTemperature Statistics:")
    print(f"  Min: {min(temperatures):.1f} °C")
    print(f"  Max: {max(temperatures):.1f} °C")
    print(f"  Mean: {np.mean(temperatures):.1f} °C")
    print(f"  Std Dev: {np.std(temperatures):.1f} °C")
    
    if sipm_voltages:
        print(f"\nSiPM Voltage Statistics:")
        print(f"  Min: {min(sipm_voltages):.1f} mV")
        print(f"  Max: {max(sipm_voltages):.1f} mV")
        print(f"  Mean: {np.mean(sipm_voltages):.1f} mV")
        print(f"  Std Dev: {np.std(sipm_voltages):.1f} mV")
    
    # Calculate correlations
    if len(data_points) > 10:
        # Pressure vs SiPM correlation
        pressure_sipm = [(d['pressure'], d['sipm']) for d in data_points if d['sipm'] is not None]
        if pressure_sipm:
            pressures_vals = [p[0] for p in pressure_sipm]
            sipm_vals = [p[1] for p in pressure_sipm]
            corr_pressure_sipm = np.corrcoef(pressures_vals, sipm_vals)[0, 1]
            print(f"\nPressure vs SiPM Voltage Correlation: {corr_pressure_sipm:.3f}")
        
        # Temperature vs SiPM correlation
        temp_sipm = [(d['temperature'], d['sipm']) for d in data_points if d['sipm'] is not None]
        if temp_sipm:
            temps_vals = [t[0] for t in temp_sipm]
            sipm_vals = [t[1] for t in temp_sipm]
            corr_temp_sipm = np.corrcoef(temps_vals, sipm_vals)[0, 1]
            print(f"Temperature vs SiPM Voltage Correlation: {corr_temp_sipm:.3f}")
    
    # Create plots
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Pressure distribution
    axes[0, 0].hist(pressures, bins=30, alpha=0.7, color='blue', edgecolor='black')
    axes[0, 0].set_xlabel('Pressure (Pa)')
    axes[0, 0].set_ylabel('Count')
    axes[0, 0].set_title('Pressure Distribution')
    axes[0, 0].grid(True, alpha=0.3)
    
    # Temperature distribution
    axes[0, 1].hist(temperatures, bins=30, alpha=0.7, color='red', edgecolor='black')
    axes[0, 1].set_xlabel('Temperature (°C)')
    axes[0, 1].set_ylabel('Count')
    axes[0, 1].set_title('Temperature Distribution')
    axes[0, 1].grid(True, alpha=0.3)
    
    # Temperature vs SiPM
    if temp_sipm:
        temps_plot = [t[0] for t in temp_sipm]
        sipm_plot = [t[1] for t in temp_sipm]
        axes[1, 0].scatter(temps_plot, sipm_plot, alpha=0.3, s=1)
        axes[1, 0].set_xlabel('Temperature (°C)')
        axes[1, 0].set_ylabel('SiPM Voltage (mV)')
        axes[1, 0].set_title(f'Temperature vs SiPM (corr={corr_temp_sipm:.3f})')
        axes[1, 0].grid(True, alpha=0.3)
    
    # Pressure vs SiPM
    if pressure_sipm:
        pressures_plot = [p[0] for p in pressure_sipm]
        sipm_plot = [p[1] for p in pressure_sipm]
        axes[1, 1].scatter(pressures_plot, sipm_plot, alpha=0.3, s=1)
        axes[1, 1].set_xlabel('Pressure (Pa)')
        axes[1, 1].set_ylabel('SiPM Voltage (mV)')
        axes[1, 1].set_title(f'Pressure vs SiPM (corr={corr_pressure_sipm:.3f})')
        axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    output_file = os.path.join(output_dir, 'environmental_correlations.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n✓ Saved environmental correlations plot: {output_file}")
    plt.close()
    
    return {
        'data_points': len(data_points),
        'pressure_range': (min(pressures), max(pressures)),
        'temperature_range': (min(temperatures), max(temperatures)),
        'corr_temp_sipm': corr_temp_sipm if temp_sipm else None,
        'corr_pressure_sipm': corr_pressure_sipm if pressure_sipm else None
    }

def analyze_temporal_patterns(documents, output_dir):
    """Analyze temporal patterns (detection rate over time)"""
    print("\n=== Temporal Pattern Analysis ===")
    
    # Extract timestamps
    events_by_hour = defaultdict(int)
    events_by_day = defaultdict(int)
    
    for d in documents:
        timestamp_ms = d.get('timestamp_ms')
        if timestamp_ms:
            try:
                dt = datetime.fromtimestamp(timestamp_ms / 1000)
                hour_key = dt.strftime('%Y-%m-%d %H:00')
                day_key = dt.strftime('%Y-%m-%d')
                events_by_hour[hour_key] += 1
                events_by_day[day_key] += 1
            except (ValueError, OSError):
                pass
    
    if not events_by_hour:
        print("⚠ No valid timestamp data available")
        return None
    
    print(f"Time range: {min(events_by_hour.keys())} to {max(events_by_hour.keys())}")
    print(f"Total hours with data: {len(events_by_hour)}")
    
    # Calculate detection rates
    hourly_rates = list(events_by_hour.values())
    daily_rates = list(events_by_day.values())
    
    print(f"\nDetection Rate Statistics:")
    print(f"  Hourly average: {np.mean(hourly_rates):.1f} events/hour")
    print(f"  Hourly min: {min(hourly_rates)} events/hour")
    print(f"  Hourly max: {max(hourly_rates)} events/hour")
    print(f"  Daily average: {np.mean(daily_rates):.1f} events/day")
    
    # Create plots
    fig, axes = plt.subplots(2, 1, figsize=(14, 8))
    
    # Hourly detection rate
    sorted_hours = sorted(events_by_hour.items())
    hours = [h[0] for h in sorted_hours]
    counts = [h[1] for h in sorted_hours]
    
    axes[0].plot(range(len(counts)), counts, marker='o', markersize=2, linewidth=0.5)
    axes[0].set_xlabel('Time (hours)')
    axes[0].set_ylabel('Events per Hour')
    axes[0].set_title('Detection Rate Over Time (Hourly)')
    axes[0].grid(True, alpha=0.3)
    axes[0].axhline(y=np.mean(counts), color='r', linestyle='--', label=f'Mean: {np.mean(counts):.1f}')
    axes[0].legend()
    
    # Daily detection rate
    sorted_days = sorted(events_by_day.items())
    days = [d[0] for d in sorted_days]
    day_counts = [d[1] for d in sorted_days]
    
    axes[1].bar(range(len(day_counts)), day_counts, alpha=0.7, color='green', edgecolor='black')
    axes[1].set_xlabel('Day')
    axes[1].set_ylabel('Events per Day')
    axes[1].set_title('Detection Rate Over Time (Daily)')
    axes[1].set_xticks(range(len(days)))
    axes[1].set_xticklabels([d.split('-')[2] for d in days], rotation=45)
    axes[1].grid(True, alpha=0.3, axis='y')
    axes[1].axhline(y=np.mean(day_counts), color='r', linestyle='--', label=f'Mean: {np.mean(day_counts):.1f}')
    axes[1].legend()
    
    plt.tight_layout()
    output_file = os.path.join(output_dir, 'temporal_patterns.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n✓ Saved temporal patterns plot: {output_file}")
    plt.close()
    
    return {
        'time_range': (min(events_by_hour.keys()), max(events_by_hour.keys())),
        'total_hours': len(events_by_hour),
        'hourly_avg': np.mean(hourly_rates),
        'daily_avg': np.mean(daily_rates),
        'hourly_min': min(hourly_rates),
        'hourly_max': max(hourly_rates)
    }

def main():
    """Main analysis function"""
    print("=" * 60)
    print("Scientific Analysis of CosmicWatch Data")
    print("=" * 60)
    
    # Determine data file location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.join(script_dir, 'data', 'cosmicwatch_data_export.json')
    
    if not os.path.exists(data_file):
        print(f"Error: {data_file} not found")
        print("Please run export_cosmicwatch_data.py first")
        sys.exit(1)
    
    # Load data
    print(f"\nLoading data from {data_file}...")
    documents = load_data(data_file)
    if not documents:
        sys.exit(1)
    
    print(f"Loaded {len(documents):,} documents\n")
    
    # Create output directory
    output_dir = os.path.join(script_dir, 'data', 'analysis')
    os.makedirs(output_dir, exist_ok=True)
    
    # Run analyses
    results = {}
    
    # Energy spectrum analysis
    results['energy_spectrum'] = analyze_energy_spectrum(documents, output_dir)
    
    # Coincidence rate analysis
    results['coincidence_rate'] = analyze_coincidence_rate(documents)
    
    # Environmental correlations
    results['environmental'] = analyze_environmental_correlations(documents, output_dir)
    
    # Temporal patterns
    results['temporal'] = analyze_temporal_patterns(documents, output_dir)
    
    # Save results summary
    summary_file = os.path.join(output_dir, 'analysis_summary.json')
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print("\n" + "=" * 60)
    print("Scientific Analysis Complete!")
    print("=" * 60)
    print(f"\nResults saved to: {output_dir}")
    print(f"Summary: {summary_file}")
    
    return results

if __name__ == '__main__':
    main()

