"""Content-addressed evidence exports, without claiming authentication."""

import hashlib
import json


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def package_case(events, source_hash, model_hash, configuration):
    links = []
    previous = "0" * 64
    for event in events:
        body = {"previous_sha256": previous, "event": event}
        previous = digest(body)
        links.append({**body, "sha256": previous})
    body = {
        "schema": "can-trace-case/1",
        "source_sha256": source_hash,
        "model_sha256": model_hash,
        "configuration": configuration,
        "chain": links,
        "integrity_scope": "detects changes against a trusted retained digest; does not authenticate acquisition, origin, time or custody",
    }
    return {"case": body, "case_sha256": digest(body)}


def verify_case(bundle):
    try:
        if digest(bundle["case"]) != bundle["case_sha256"]:
            return False
        previous = "0" * 64
        for link in bundle["case"]["chain"]:
            body = {"previous_sha256": link["previous_sha256"], "event": link["event"]}
            if link["previous_sha256"] != previous or digest(body) != link["sha256"]:
                return False
            previous = link["sha256"]
        return True
    except (KeyError, TypeError, ValueError):
        return False
