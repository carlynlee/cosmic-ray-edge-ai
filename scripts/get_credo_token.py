#!/usr/bin/env python3
"""
Get CREDO.science API Token

This script authenticates with CREDO.science API using username/password
and retrieves an API token for use in other scripts.

Usage:
    python3 get_credo_token.py --username <YOUR_CREDO_USERNAME> --password <YOUR_CREDO_PASSWORD>
"""

import argparse
import requests
import platform
import secrets
import json

def get_token(username, password, endpoint="https://api.credo.science/api/v2"):
    """Get CREDO API token using username/password"""
    
    # Generate a device ID (similar to data-exporter)
    device_id = secrets.token_hex(16)
    
    base_request = {
        "device_id": device_id,
        "device_type": "credo-token-getter",
        "device_model": platform.system(),
        "system_version": platform.release(),
        "app_version": 1,
        "username": username,
        "password": password
    }
    
    try:
        response = requests.post(
            f"{endpoint}/user/login",
            json=base_request,
            timeout=30
        )
        
        if not response.ok:
            error_data = response.json() if response.content else {}
            print(f"Error authenticating: {error_data}")
            response.raise_for_status()
        
        token = response.json()["token"]
        return token
        
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to CREDO API: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(
        description='Get CREDO.science API token'
    )
    parser.add_argument(
        '--username', '-u',
        required=True,
        help='CREDO.science username'
    )
    parser.add_argument(
        '--password', '-p',
        required=True,
        help='CREDO.science password'
    )
    parser.add_argument(
        '--endpoint',
        default='https://api.credo.science/api/v2',
        help='CREDO API endpoint'
    )
    parser.add_argument(
        '--save-secret',
        action='store_true',
        help='Save token to Kubernetes secret (requires kubectl)'
    )
    parser.add_argument(
        '--namespace',
        default='cblee-credo',
        help='Kubernetes namespace for secret'
    )
    
    args = parser.parse_args()
    
    print("Getting CREDO API token...")
    print(f"Username: {args.username}")
    print(f"Endpoint: {args.endpoint}")
    
    try:
        token = get_token(args.username, args.password, args.endpoint)
        
        print("\n" + "=" * 70)
        print("✓ Token retrieved successfully!")
        print("=" * 70)
        print(f"\nToken: {token}")
        print("\nTo use this token:")
        print(f"  export CREDO_TOKEN='{token}'")
        
        if args.save_secret:
            import subprocess
            print("\nSaving to Kubernetes secret...")
            try:
                # Create or update secret
                result = subprocess.run(
                    [
                        'kubectl', 'create', 'secret', 'generic', 'credo-token',
                        '--from-literal=token=' + token,
                        '-n', args.namespace,
                        '--dry-run=client', '-o', 'yaml'
                    ],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                # Apply it
                apply_result = subprocess.run(
                    ['kubectl', 'apply', '-f', '-'],
                    input=result.stdout,
                    text=True,
                    check=True
                )
                
                print(f"✓ Token saved to Kubernetes secret 'credo-token' in namespace '{args.namespace}'")
                print("\nTo update the deployment:")
                print(f"  kubectl rollout restart deployment/credo-stream -n {args.namespace}")
                
            except subprocess.CalledProcessError as e:
                print(f"✗ Error saving to Kubernetes: {e}")
                print("You can manually create the secret:")
                print(f"  kubectl create secret generic credo-token \\")
                print(f"    --from-literal=token='{token}' \\")
                print(f"    -n {args.namespace}")
        else:
            print("\nTo save to Kubernetes secret, run:")
            print(f"  python3 get_credo_token.py --username {args.username} --password '{args.password}' --save-secret")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())




