# QUIC Server Setup Issues

**Problem:** cloudflare-quiche server is failing with `TlsFail` error.

**Root Cause:** The quiche-server expects separate certificate and key files, not a combined PEM file.

---

## ✅ **Correct Setup**

### **1. Generate Separate Cert Files**
```bash
mkdir -p /tmp/quic_test/certs
cd /tmp/quic_test/certs

# Generate private key
openssl genrsa -out server.key 2048

# Generate self-signed certificate
openssl req -new -x509 -key server.key -out server.crt -days 365 -subj "/CN=localhost"

# Create a minimal index file (required by quiche)
touch index
```

### **2. Start Server with Correct Options**
```bash
cd /tmp/quic_test

/opt/homebrew/bin/quiche-server \
    --listen=127.0.0.1:4433 \
    --cert=certs/server.crt \
    --key=certs/server.key \
    --root=certs/ \
    --dump-packets logs/
```

### **3. Expected Output**
```
Listening on 127.0.0.1:4433
```

---

## ❌ **What NOT To Do**

- **Don't combine cert and key** into one file
- **Don't use relative paths** without full paths
- **Don't omit the --root** option

---

## 🎯 **Alternative: Use Existing Certificate**

If the quiche installation has sample certificates:
```bash
# Check if quiche comes with sample certs
cd /opt/homebrew/Cellar/cloudflare-quiche/0.29.2
find . -name "*.crt" -o -name "*.key"

# Or use the source directory certs if available
cd /opt/homebrew/Cellar/cloudflare-quiche/0.29.2/src
ls -la certs/
```

---

## 📋 **Next Steps**

1. **Fix certificate setup** with separate files
2. **Test server startup** without payload
3. **Then add payload testing**
4. **Integrate with Suricata detection**

---

**The quiche-server requires specific TLS setup. Once certificates are correct, testing can proceed.**
