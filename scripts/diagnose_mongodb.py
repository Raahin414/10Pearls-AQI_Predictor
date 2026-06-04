"""Detailed MongoDB Atlas connectivity diagnostics.

The utility intentionally separates DNS, SRV, TCP, TLS, authentication, and CRUD
checks so connectivity failures can be attributed to the right layer.
"""

from __future__ import annotations

import argparse
import os
import socket
import ssl
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, quote_plus, urlparse, urlunparse

sys.path.append(str(Path(__file__).resolve().parents[1]))

import certifi
import dns.resolver
from gridfs import GridFS
from dotenv import load_dotenv
from pymongo import MongoClient

from karachi_aqi.config.settings import get_settings


DIAGNOSTIC_COLLECTION = "_diagnostics"


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def redact_uri(uri: str) -> str:
    parsed = urlparse(uri)
    if "@" not in parsed.netloc:
        return uri
    userinfo, host = parsed.netloc.rsplit("@", 1)
    username = userinfo.split(":", 1)[0]
    redacted_netloc = f"{username}:***@{host}"
    return urlunparse((parsed.scheme, redacted_netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))


def resolve_settings(uri_arg: str | None, database_arg: str | None) -> tuple[str, str]:
    load_dotenv()
    if uri_arg:
        uri = uri_arg
        database = database_arg or os.getenv("MONGODB_DATABASE", "karachi_aqi")
        return uri, database

    settings = get_settings()
    return settings.resolved_mongodb_uri, database_arg or settings.mongodb_database


def parsed_host(uri: str) -> tuple[str, bool]:
    parsed = urlparse(uri)
    return parsed.hostname or "", parsed.scheme == "mongodb+srv"


def standardize_uri(uri: str) -> str:
    parsed = urlparse(uri)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params.setdefault("retryWrites", "true")
    params.setdefault("w", "majority")
    params.setdefault("appName", "KarachiAQIDiagnostics")
    query = "&".join(f"{quote_plus(key)}={quote_plus(value)}" for key, value in params.items())
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, query, parsed.fragment))


def run_check(results: list[CheckResult], name: str, fn):
    try:
        detail = fn()
        results.append(CheckResult(name, True, detail if detail is not None else "ok"))
    except Exception as exc:
        results.append(CheckResult(name, False, f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"))


def dns_a_lookup(host: str) -> str:
    records = sorted({item[4][0] for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)})
    return ", ".join(records)


def dns_srv_lookup(host: str) -> tuple[str, list[tuple[str, int]]]:
    answers = dns.resolver.resolve(f"_mongodb._tcp.{host}", "SRV")
    targets = sorted((str(answer.target).rstrip("."), int(answer.port)) for answer in answers)
    detail = ", ".join(f"{target}:{port}" for target, port in targets)
    return detail, targets


def dns_txt_lookup(host: str) -> str:
    try:
        answers = dns.resolver.resolve(host, "TXT")
    except dns.resolver.NoAnswer:
        return "no TXT records"
    return " | ".join(b"".join(answer.strings).decode("utf-8", errors="replace") for answer in answers)


def tcp_check(host: str, port: int, timeout: float = 8.0) -> str:
    with socket.create_connection((host, port), timeout=timeout):
        return f"connected to {host}:{port}"


def tls_check(host: str, port: int, timeout: float = 8.0) -> str:
    context = ssl.create_default_context(cafile=certifi.where())
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    with socket.create_connection((host, port), timeout=timeout) as raw:
        with context.wrap_socket(raw, server_hostname=host) as wrapped:
            cert = wrapped.getpeercert()
            subject = cert.get("subject", [])
            return f"TLS {wrapped.version()} {wrapped.cipher()[0]} subject={subject}"


def minimal_client(uri: str) -> MongoClient:
    return MongoClient(
        standardize_uri(uri),
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000,
        tlsCAFile=certifi.where(),
    )


def mongo_ping(uri: str) -> str:
    client = minimal_client(uri)
    client.admin.command("ping")
    return "ping ok"


def list_databases(uri: str) -> str:
    client = minimal_client(uri)
    names = client.list_database_names()
    return ", ".join(names) if names else "no databases visible"


def list_collections(uri: str, database: str) -> str:
    client = minimal_client(uri)
    names = client[database].list_collection_names()
    return ", ".join(names) if names else "no collections visible"


def crud_check(uri: str, database: str) -> str:
    client = minimal_client(uri)
    collection = client[database][DIAGNOSTIC_COLLECTION]
    marker = f"diag-{datetime.now(timezone.utc).isoformat()}"
    insert_result = collection.insert_one({"marker": marker, "created_at": datetime.now(timezone.utc), "status": "new"})
    found = collection.find_one({"_id": insert_result.inserted_id})
    if not found:
        raise RuntimeError("inserted diagnostic document could not be read back")
    update_result = collection.update_one({"_id": insert_result.inserted_id}, {"$set": {"status": "updated"}})
    if update_result.modified_count != 1:
        raise RuntimeError(f"expected one update, got {update_result.modified_count}")
    delete_result = collection.delete_one({"_id": insert_result.inserted_id})
    if delete_result.deleted_count != 1:
        raise RuntimeError(f"expected one delete, got {delete_result.deleted_count}")
    return f"insert/read/update/delete ok in {database}.{DIAGNOSTIC_COLLECTION}"


def gridfs_check(uri: str, database: str) -> str:
    client = minimal_client(uri)
    fs = GridFS(client[database])
    payload = b"karachi-aqi-gridfs-diagnostic"
    file_id = fs.put(payload, filename="_diagnostic_gridfs.bin")
    loaded = fs.get(file_id).read()
    if loaded != payload:
        raise RuntimeError("GridFS payload did not round-trip correctly")
    fs.delete(file_id)
    if fs.exists(file_id):
        raise RuntimeError("GridFS diagnostic file was not deleted")
    return f"gridfs write/read/delete ok in {database}.fs"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MongoDB Atlas diagnostics.")
    parser.add_argument("--uri", default=None, help="MongoDB URI. Defaults to environment settings.")
    parser.add_argument("--database", default=None, help="Database name. Defaults to MONGODB_DATABASE or karachi_aqi.")
    args = parser.parse_args()

    uri, database = resolve_settings(args.uri, args.database)
    host, is_srv_uri = parsed_host(uri)
    results: list[CheckResult] = []
    srv_targets: list[tuple[str, int]] = []

    print("MongoDB Diagnostics")
    print(f"Python: {sys.version.split()[0]}")
    print(f"OpenSSL: {ssl.OPENSSL_VERSION}")
    print(f"certifi: {certifi.where()}")
    print(f"URI: {redact_uri(standardize_uri(uri))}")
    print(f"Database: {database}")
    print()

    if is_srv_uri:
        results.append(
            CheckResult(
                "DNS A/AAAA lookup",
                True,
                "skipped direct host lookup: mongodb+srv uses _mongodb._tcp SRV records",
            )
        )
    else:
        run_check(results, "DNS A/AAAA lookup", lambda: dns_a_lookup(host))
    def srv_step() -> str:
        nonlocal srv_targets
        detail, srv_targets = dns_srv_lookup(host)
        return detail

    run_check(results, "Atlas SRV lookup", srv_step)
    run_check(results, "Atlas TXT lookup", lambda: dns_txt_lookup(host))

    for target, port in srv_targets:
        run_check(results, f"TCP {target}:{port}", lambda target=target, port=port: tcp_check(target, port))
        run_check(results, f"TLS {target}:{port}", lambda target=target, port=port: tls_check(target, port))

    run_check(results, "PyMongo ping/auth", lambda: mongo_ping(uri))
    run_check(results, "Database listing", lambda: list_databases(uri))
    run_check(results, "Collection listing", lambda: list_collections(uri, database))
    run_check(results, "CRUD insert/read/update/delete", lambda: crud_check(uri, database))
    run_check(results, "GridFS write/read/delete", lambda: gridfs_check(uri, database))

    failed = 0
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] {result.name}")
        print(result.detail)
        print()
        failed += 0 if result.ok else 1

    print(f"Summary: {len(results) - failed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
