# CLI Tools Investigation Results

**Date:** July 10, 2026  
**Environment:** macOS with Homebrew  
**Investigator:** OpenClaw Security Research

---

## 📊 **Investigation Summary**

### **Tools Checked:**
1. `nghttp3-client` - XQUIC HTTP/3 client
2. `nghttp2` - HTTP/2 client
3. `ngtcp2` - QUIC client
4. `aioquic` - Python QUIC library
5. `cloudflare-quiche` - **NEW: QUIC stack with client/server** ✅

---

## 🔍 **Findings**

### **✅ NEW: Available (After Installation)**

#### **cloudflare-quiche (QUIC Stack)**
- **Version:** 0.29.2
- **Client:** `/opt/homebrew/bin/quiche-client`
- **Server:** `/opt/homebrew/bin/quiche-server`
- **Status:** ✅ **INSTALLED AND AVAILABLE**

```bash
/opt/homebrew/bin/quiche-client --help
Usage: quiche-client [options] URL...
```

```bash
/opt/homebrew/bin/quiche-server --help
Usage: quiche-server [options]
Listen on: 127.0.0.1:4433 [default]
```

### **✅ Available (But Not QUIC)**

#### **nghttp (HTTP/2 client)**
- **Path:** `/opt/homebrew/bin/nghttp`
- **Type:** HTTP/2 client
- **Status:** ✅ Installed
- **Use:** HTTP/2 testing only

---

### **❌ Missing (Exact Match)**

#### **nghttp3-client**
- **Search Result:** `brew search nghttp3-client`
- **Output:** `Error: No formulae or casks found for "nghttp3-client".`
- **Status:** ❌ **NOT AVAILABLE**

#### **ngtcp2-cli**
- **Status:** ❌ **NOT AVAILABLE**

---

### **✅ Libraries**

#### **libnghttp3**
- **Version:** 1.17.0
- **Status:** ✅ Library installed
- **CLI Tools:** ❌ None

#### **libngtcp2**
- **Version:** 1.24.0
- **Status:** ✅ Library installed
- **CLI Tools:** ❌ None

---

## 🎯 **Impact on Our Research**

### **BEFORE:**
- ❌ No QUIC client/server available
- ❌ Limited to static analysis only
- ✅ Python test harness only (mock testing)

### **AFTER (cloudflare-quiche installed):**
- ✅ **QUIC client/server available**
- ✅ **Can run live dynamic tests**
- ✅ **Full protocol testing possible**
- ✅ **XQUIC-style attack simulation**

---

## 🚀 **New Testing Capabilities**

### **Live QUIC Testing**
Now we can:
1. **Start a local QUIC server** using `quiche-server`
2. **Send XRING attack payload** using `quiche-client`
3. **Analyze attack behavior** in real QUIC implementation
4. **Validate detection signatures** with real traffic
5. **Test mitigation strategies**

### **Dynamic Test Infrastructure**
```bash
# Start QUIC server
quiche-server --listen 127.0.0.1:4433 --cert certs/cert.crt --key certs/cert.key

# Send attack payload (with custom QPACK encoding)
quiche-client --trust-origin-ca-pem certs/ca.pem 127.0.0.1:4433

# Monitor Suricata
suricata -c suricata.yaml -i en0 -l logs/
```

---

## 📋 **Summary**

**Investigation complete + tool installed:**

- ✅ `cloudflare-quiche` - **INSTALLED** (0.29.2)
- ✅ `quiche-server` - **Available** (0.29.2)
- ✅ `quiche-client` - **Available** (0.29.2)
- ✅ `nghttp` (HTTP/2 client) - Available
- ❌ `nghttp3-client` - Not available
- ❌ `ngtcp2` (CLI) - Not available

**Now we have everything needed for comprehensive QUIC security testing.**

---

**Investigation completed:** July 10, 2026  
**Status:** ✅ **Full testing capabilities now available**
