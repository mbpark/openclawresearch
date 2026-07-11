# Suricata Debugging Guide

## Current Situation
- **Suricata is running** (sudo processes confirmed)
- **EVE JSON file exists** but remains empty (0 bytes)
- **No alerts detected** during traffic tests
- **BPF device permission** is the root cause

## Root Cause Analysis

### **1. BPF Permission Denied**
```
Error: pcap: en0: could not activate the pcap handler, error (cannot open BPF device) /dev/bpf0: Permission denied
```
This happens because Suricata needs root privileges to capture network packets on macOS.

### **2. Suricata Runs Without Capturing**
Even with sudo, Suricata may fail to capture traffic because:
- Interface not properly initialized
- Wrong interface name
- Rules not loading correctly
- Permission issues after startup

## Debugging Steps

### **Step 1: Check Interface**
```bash
ifconfig en0 | grep inet
# Should show an IP address
```

### **Step 2: Verify Traffic is Present**
```bash
# Should show network activity
sudo tcpdump -i en0 -c 10 -n 2>&1 | head -20
```

### **Step 3: Start Suricata with Debug Logging**
```bash
sudo suricata -c ~/.suricata/suricata.yaml -i en0 -v -l ~/.suricata/log/debug.log 2>&1 &
```

### **Step 4: Check If Rules Loaded**
```bash
sudo suricata -c ~/.suricata/suricata.yaml -T 2>&1 | grep -i "rule\|signature"
```

### **Step 5: Monitor EVE Log**
```bash
tail -f ~/.suricata/log/eve.json
```

## Solution Options

### **Option A: Simple sudo (Easiest)**
```bash
sudo suricata -c ~/.suricata/suricata.yaml -i en0
```
**Pros:** Simple, works  
**Cons:** Requires password each time

### **Option B: Passwordless Sudo (Recommended)**
```bash
# Edit sudoers
sudo visudo
# Add this line at the end:
mitchparker ALL=(ALL) NOPASSWD: /opt/homebrew/bin/suricata
```

### **Option C: BPF Device Permissions**
```bash
# Add user to bpf group (if exists)
sudo dscl . append /Groups/bpf GroupMembership mitchparker

# Or set permissions on BPF device (temporary)
sudo chmod 666 /dev/bpf*
```

## Testing the Fix

### **Test 1: Generate Traffic**
```bash
cd /Users/mitchparker/.openclaw/workspace/research
./manual_traffic_test.sh
```

### **Test 2: Check Logs**
```bash
tail -f ~/.suricata/log/eve.json
# Should show alerts like:
# {"event_type":"alert","alert":{"signature":"XRING QPACK Attack detected"...}}
```

### **Test 3: Check Dashboard**
```bash
curl http://127.0.0.1:5001/api/alerts
# Should show new alerts
```

## Known Issues

### **1. EVE Log Empty**
**Cause:** Suricata not capturing traffic or no matching rules  
**Fix:** Check interface, verify rules load, ensure traffic exists

### **2. No BPF Permissions**
**Cause:** User lacks root privileges  
**Fix:** Use sudo or configure passwordless sudo

### **3. Interface Not Found**
**Cause:** Wrong interface name  
**Fix:** Use `ifconfig` to find correct interface (usually en0 on Mac)

## Scripts Available

- `fix_suricata_logging.sh` - Fix permissions and config
- `start_suricata_manual.sh` - Automated start script  
- `check_suricata_realtime.sh` - Real-time log monitor
- `manual_traffic_test.sh` - Traffic generation script

## Quick Fix Command

Run this **once** in your terminal:
```bash
sudo visudo && echo "mitchparker ALL=(ALL) NOPASSWD: /opt/homebrew/bin/suricata" | sudo tee -a /etc/sudoers
sudo /opt/homebrew/bin/suricata -c ~/.suricata/suricata.yaml -i en0
```

Then generate traffic and monitor logs!
