# MongoDB Diagnostics

This project includes three independent MongoDB verification utilities:

```bash
python scripts/diagnose_mongodb.py
python scripts/minimal_mongodb_ping.py
node scripts/compass_equivalent_node_check.cjs
```

All utilities load MongoDB settings from environment variables. Use `MONGODB_URI` for the least ambiguous test:

```bash
export MONGODB_URI='mongodb+srv://<username>:<password>@aqiproject.5cqik42.mongodb.net/?retryWrites=true&w=majority&appName=KarachiAQI'
export MONGODB_DATABASE='karachi_aqi'
python scripts/diagnose_mongodb.py
```

## Diagnostic Coverage

- `mongodb+srv` URI parsing and redaction
- DNS/SRV/TXT lookup
- TCP connectivity to each Atlas shard endpoint
- TLS handshake with the `certifi` CA bundle
- PyMongo ping/authentication
- Database listing
- Collection listing
- Insert/read/update/delete using `_diagnostics`
- GridFS write/read/delete using the `fs` bucket

## Current Verified Evidence

Observed from this environment on June 3, 2026:

- Public IP: `103.196.163.220`
- OS: macOS 15.6 / Darwin 24.6.0
- Project Python: 3.9.6 with LibreSSL 2.8.3
- Clean Python control environment: 3.12.13 with OpenSSL 3.5.5
- PyMongo: 4.17.0
- `certifi`: 2026.5.20
- Proxy settings: no shell proxy variables and empty macOS proxy configuration

Final diagnostic result:

```text
[PASS] Atlas SRV lookup
[PASS] Atlas TXT lookup
[PASS] TCP ac-dgwrfrt-shard-00-00.5cqik42.mongodb.net:27017
[PASS] TLS ac-dgwrfrt-shard-00-00.5cqik42.mongodb.net:27017
[PASS] TCP ac-dgwrfrt-shard-00-01.5cqik42.mongodb.net:27017
[PASS] TLS ac-dgwrfrt-shard-00-01.5cqik42.mongodb.net:27017
[PASS] TCP ac-dgwrfrt-shard-00-02.5cqik42.mongodb.net:27017
[PASS] TLS ac-dgwrfrt-shard-00-02.5cqik42.mongodb.net:27017
[PASS] PyMongo ping/auth
[PASS] Database listing
[PASS] Collection listing
[PASS] CRUD insert/read/update/delete
[PASS] GridFS write/read/delete
Summary: 14 passed, 0 failed
```

The Compass-equivalent Node driver check returned `{"ok":1}`. The clean external Python virtual environment also returned `{'ok': 1}` for a minimal PyMongo ping.

## Root-Cause Conclusion

MongoDB Atlas is reachable and working from this machine. The earlier `TLSV1_ALERT_INTERNAL_ERROR` was not caused by Atlas network access, Atlas authentication, DNS, or database permissions.

The fix applied in the repository was:

- pin PyMongo to 4.17.0;
- pin `certifi` and pass `tlsCAFile=certifi.where()` when creating `MongoClient`;
- use the exact SRV URI from the runtime environment;
- keep credentials outside source files;
- add independent diagnostics for Python, Node/Compass-equivalent, DNS, TCP, TLS, auth, CRUD, and GridFS.

During live training, a separate persistence issue was discovered: serialized model artifacts exceeded MongoDB's 16 MB BSON document limit. Model and scaler pickles are now stored in GridFS, while `model_registry` stores lightweight metadata and GridFS file references.
