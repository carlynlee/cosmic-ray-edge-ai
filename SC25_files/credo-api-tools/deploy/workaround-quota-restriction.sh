#!/bin/bash

# Workarounds for NRP Quota Restriction
# The error "Your pods resources utilization is too low" suggests NRP requires minimum resource utilization

set -euo pipefail

NAMESPACE="cblee-credo"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "=========================================="
echo "NRP Quota Restriction Workarounds"
echo "=========================================="
echo ""
echo "The error 'Your pods resources utilization is too low' suggests:"
echo "  - NRP requires minimum resource utilization per account"
echo "  - SC25 nodes may have quota exemptions"
echo ""
echo "Available workarounds:"
echo ""

# Workaround 1: Patch existing deployments instead of creating new ones
echo "1. PATCH EXISTING DEPLOYMENTS (Recommended)"
echo "   Instead of deleting and recreating, patch node affinity:"
echo ""
cat << 'EOF'
   # Remove SC25 node affinity from existing deployments
   kubectl patch deployment caltech-fl-server -n cblee-credo --type='json' \
     -p='[{"op": "remove", "path": "/spec/template/spec/affinity"}]'
   
   kubectl patch deployment caltech-fl-server -n cblee-credo --type='json' \
     -p='[{"op": "remove", "path": "/spec/template/spec/tolerations"}]'
   
   # Add node affinity to exclude SC25 nodes
   kubectl patch deployment caltech-fl-server -n cblee-credo --type='json' \
     -p='[{"op": "add", "path": "/spec/template/spec/affinity", "value": {
       "nodeAffinity": {
         "requiredDuringSchedulingIgnoredDuringExecution": {
           "nodeSelectorTerms": [{
             "matchExpressions": [{
               "key": "kubernetes.io/hostname",
               "operator": "NotIn",
               "values": ["r640-01.sc25.nrp-nautilus.io", "rc3-sc-13.sc25.nrp-nautilus.io", 
                         "rc3-sc-14.sc25.nrp-nautilus.io", "rc3-sc-15.sc25.nrp-nautilus.io"]
             }]
           }]
         }
       }
     }}]'
EOF
echo ""

# Workaround 2: Use node selector to exclude SC25
echo "2. USE NODE SELECTOR TO EXCLUDE SC25"
echo "   Add node selector that excludes SC25 nodes:"
echo ""
cat << 'EOF'
   # Add label to non-SC25 nodes (if you have permission)
   # Or use existing labels to select non-SC25 nodes
   
   # Example: Select nodes without SC25 in hostname
   nodeSelector:
     nautilus.io/reservation: "!scinet"
EOF
echo ""

# Workaround 3: Reduce resource requests temporarily
echo "3. REDUCE RESOURCE REQUESTS (May help if quota is based on requests)"
echo "   Temporarily reduce CPU/memory requests:"
echo ""
cat << 'EOF'
   kubectl patch deployment caltech-fl-server -n cblee-credo --type='json' \
     -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/requests/cpu", "value": "2"}]'
   
   kubectl patch deployment caltech-fl-server -n cblee-credo --type='json' \
     -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/requests/memory", "value": "8Gi"}]'
EOF
echo ""

# Workaround 4: Deploy one at a time
echo "4. DEPLOY ONE POD AT A TIME"
echo "   The quota check might be cumulative - try deploying pods sequentially:"
echo ""
cat << 'EOF'
   # Deploy FL server first
   # Wait for it to be running
   # Then deploy clients one by one
EOF
echo ""

# Workaround 5: Use different namespace
echo "5. TRY DIFFERENT NAMESPACE"
echo "   Quota might be namespace-specific:"
echo ""
cat << 'EOF'
   # Create new namespace
   kubectl create namespace credo-fl-test
   
   # Deploy to new namespace (modify scripts to use new namespace)
EOF
echo ""

# Workaround 6: Check account status
echo "6. CHECK YOUR NRP ACCOUNT STATUS"
echo "   Visit: https://nrp.ai/userinfo/"
echo "   Check resource utilization and quota limits"
echo ""

# Workaround 7: Contact NRP support
echo "7. CONTACT NRP SUPPORT"
echo "   Request quota increase or exemption for non-SC25 nodes"
echo "   NRP Support: https://nrp.ai/support/"
echo ""

# Interactive menu
echo "=========================================="
echo "Which workaround would you like to try?"
echo "=========================================="
echo "1. Patch existing deployments (remove SC25 affinity)"
echo "2. Show detailed patch commands"
echo "3. Check current pod locations"
echo "4. Exit"
echo ""
read -p "Enter choice [1-4]: " choice

case $choice in
    1)
        log_info "Patching existing deployments to remove SC25 node affinity..."
        
        for deployment in caltech-fl-server caltech-fl-client mit-fl-client udel-fl-client; do
            if kubectl get deployment -n "$NAMESPACE" "$deployment" >/dev/null 2>&1; then
                log_info "Patching $deployment..."
                
                # Remove SC25 affinity and tolerations
                kubectl patch deployment "$deployment" -n "$NAMESPACE" --type='json' \
                  -p='[{"op": "remove", "path": "/spec/template/spec/affinity"}]' 2>/dev/null || true
                
                kubectl patch deployment "$deployment" -n "$NAMESPACE" --type='json' \
                  -p='[{"op": "remove", "path": "/spec/template/spec/tolerations"}]' 2>/dev/null || true
                
                log_success "$deployment patched"
            else
                log_warning "$deployment not found"
            fi
        done
        
        log_info "Pods will be rescheduled. Check status with:"
        echo "  kubectl get pods -n $NAMESPACE -o wide"
        ;;
    2)
        echo ""
        echo "Detailed patch commands for each deployment:"
        echo ""
        for deployment in caltech-fl-server caltech-fl-client mit-fl-client udel-fl-client; do
            echo "# Patch $deployment:"
            echo "kubectl patch deployment $deployment -n $NAMESPACE --type='json' \\"
            echo "  -p='[{\"op\": \"remove\", \"path\": \"/spec/template/spec/affinity\"}]'"
            echo "kubectl patch deployment $deployment -n $NAMESPACE --type='json' \\"
            echo "  -p='[{\"op\": \"remove\", \"path\": \"/spec/template/spec/tolerations\"}]'"
            echo ""
        done
        ;;
    3)
        log_info "Current pod locations:"
        kubectl get pods -n "$NAMESPACE" -l 'app in (caltech-fl-server,caltech-fl-client,mit-fl-client,udel-fl-client)' \
          -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName,STATUS:.status.phase 2>&1
        ;;
    4)
        exit 0
        ;;
    *)
        log_error "Invalid choice"
        exit 1
        ;;
esac

