#!/usr/bin/env python3
"""Request and verify official SmartGit 26.1 Format=3 evaluations on Linux.

Protocol recovered from smartgit.ahv/ahG/aaa/ahi in SmartGit 26.1.052;
these classes are identical in the installed 26.1.056 update.
Only Syntevo's server signs credentials. No local signing keys are used.
"""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request


SERVER = "https://license.syntevo.com/v1/evaluate"
BASE64 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz<>"
BASE61 = "123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
# Pinned public verification key from smartgit.ahv.a(), not a signing key.
ROOT_MODULUS = (
    "8zi-LEMNu-baWEA-NuCGx-yckKG-yYWhC-WYQRM-yhqTb-5zYj6-e9vbq-eCgwX-g2APi-z8c35-Qgx11-BYJN3-"
    "<9Ers-2<BgQ-0oLMj-4LWJO-WGtaK-Rf55f-fjHHU-WMcHn-esyZy-vsPYx-W22jr-NwrZx-YYIQI-re55N-9sZv"
    "F-PwzWL-LC6Ct-DQoHw-xJ9ni-ZOtsL-mJw2N-kjlVu-Tacfn-CbwZE-kpoyw-CgmfZ-SJLZh-wvqkT-cCu7m->D"
    "Vfe-YTYX6-vC<K5-ZrSfp-KAuIL-MwSGZ-aqxRR-bB4j2-<Egpx-0R77Q-BiZ2U-yTd2v-YpUNe-iyDh9-QvCKp-"
    "I9XQ9-pZkvI-5zjw5-ljlui-<<oU7-0HeKJ-EVYp4-3wFnA-NmiXK-tGlmE-Zr1FK-FDUq<-tUGP<-RUk14-Fze3"
    "j-X0eyP-GvDhB-G5tuE-vhSpK-u7s1P-FdpXv-KTjnO-xZ8xg-B3zGr-pGjTM-To3xL-fsGgl-tHxvR-GM94d-il"
    "NzA-n6VoB-FksZn-klvJj-E8hKL->foko-cxbro-hlmkj-ZVcya-2nAKS-INjmZ-09hlA-U93Kz-g9BdV-QvXOj-"
    "4j3KW-e<oox-LF3nF-4E0gZ-PFL35-efmn8-VxAI4-MoN7a-2Cjsy-q6gBQ-DkBvR-jJGS2-UwQe8-1rnvt-1h6Y"
    "M-Wwavb-s>vjB-QBIYh-he5XJ-RtTss-GZVhe-jfouK-8v7sR-teks7->UW<L-SbW3U-NneQ6-TxgyK-eytIL-iy"
    "7t9-yiHx5-DNtEz-2VhcJ-y>dr7"
)
ROOT_PUBLIC = (
    "2t-hTE<k-B1Yyf-3J2fR-tDafw-DCEXp-KgTmj-KoL7R-XY6>T-WMbQy-Q1KKW-ixeXa-eayG<-f<XHC-Oh9is-7"
    "rGGe-udOip-<d5AO-xfrUH-LfBCC-vRqqa-RqqVG-4g7Nq-x0C2P-yMOEW-0Sy4Y-GRYgg-AehQN-sbJQQ-qFNEm"
    "-HGzzC-Tj8QZ-Yn>q>-E<X95-VwHYo-1pv31-HcQJT-bBMDc-0Kqg9-HjOhj-7qz9A-PuCV9-<TrEQ-8Bk7F-uIM"
    "IL-LOO7o-pPTQw-PDDUx-6uoSS-FlBfD-eCJSr-RU9zJ-<nBBd-msXDC-Q7hEj-Dmy72-dPvuI-PirEw-HAguL-M"
    "CSyq-F20vb-WhTmm-mbPNd-NPoC<-pzGfW-WEtaB-9hF>k-e4aFT-zcrvV"
)


def decode_number(text, alphabet):
    if not text:
        raise ValueError("Missing encoded integer")
    value = 0
    for char in text:
        if char != "-":
            value = value * len(alphabet) + alphabet.index(char)
    return value


def machine_hashes():
    if sys.platform != "linux":
        raise ValueError("This script implements the Linux machine binding only")
    for name in ("/var/lib/dbus/machine-id", "/etc/machine-id", "/etc/hostid"):
        try:
            data = Path(name).read_bytes()
        except OSError:
            continue
        if len(data) < 12:
            continue
        value = int.from_bytes(hashlib.sha512(data).digest()[:12], "big")
        encoded = ""
        while value:
            value, digit = divmod(value, 61)
            encoded = BASE61[digit] + encoded
        return {"umi": encoded or BASE61[0]}
    raise ValueError("No supported Linux machine ID is available")


def verify(data, hashes):
    """Verify signatures and binding, returning dates without changing the file."""
    fields = {}
    body = []
    signature_lines = []
    for line in data.decode("utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            if key in fields:
                raise ValueError("Duplicate credential field: " + key)
            fields[key] = value
            body.append(line)
            signature_lines = []
        elif len(line) == 80:
            signature_lines.append(line)
        else:
            raise ValueError("Unsupported credential line format")

    if fields.get("Format") != "3" or fields.get("Kind") != "evaluation":
        raise ValueError("Expected a Format=3 evaluation credential")
    if any(key in fields for key in (
            "DerivedPrivate", "DerivedSignature", "Signature", "Key")):
        raise ValueError("Unsupported signature variant")
    modulus = decode_number(fields["DerivedModulus"], BASE64)
    public = decode_number(fields["DerivedPublic"], BASE64)
    master_signature = decode_number(fields["DerivedMasterSignature"], BASE64)
    # Java BigInteger.toByteArray() includes a sign byte when necessary.
    modulus_bytes = modulus.to_bytes((modulus.bit_length() + 8) // 8, "big")
    expected = int.from_bytes(hashlib.sha512(modulus_bytes).digest(), "big")
    if pow(master_signature, decode_number(ROOT_PUBLIC, BASE64),
           decode_number(ROOT_MODULUS, BASE64)) != expected:
        raise ValueError("Invalid derived-key master signature")
    # The 80-column trailer uses base 61, with '0' padding; it is not Base64.
    signature = decode_number("".join(signature_lines).rstrip("0"), BASE61)
    expected = int.from_bytes(
        hashlib.sha512("".join(body).encode("utf-8")).digest(), "big")
    if pow(signature, public, modulus) != expected:
        raise ValueError("Invalid credential body signature")
    if fields["Product"] != "SmartGit" or fields["MajorVersion"] != "26.1":
        raise ValueError("Credential product or major version does not match")
    if hashes.get(fields["MachineId"]) != fields["MachineValue"]:
        raise ValueError("Credential does not match this machine")
    if not fields["EvaluationId"]:
        raise ValueError("Missing evaluation ID")
    until = datetime.date.fromisoformat(fields["ValidUntil"])
    # Mirrors ZY.b("ValidUntil", true): local midnight plus 86,340 seconds.
    expiry = datetime.datetime.combine(until, datetime.time()).timestamp() + 86340
    return {
        "product": fields["Product"],
        "major_version": fields["MajorVersion"],
        "valid_until": until.isoformat(),
        "signed_at": fields.get("SignedAt"),
        "expired": datetime.datetime.now().timestamp() > expiry,
        "signatures_valid": True,
        "machine_binding_matches": True,
    }


def request_evaluation(build, hashes):
    payload = {
        "Product": "SmartGit",
        "MajorVersion": "26.1",
        "Build": build,
        "OperatingSystem": "linux",
        "HardwareHashes": hashes,
        # This script does not reproduce the application's VM classifier.
        "AdditionalData": {},
    }
    request = urllib.request.Request(
        SERVER, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        try:
            code = json.loads(error.read()).get("errorCode", "unspecified")
        except (ValueError, AttributeError):
            code = "unspecified"
        raise ValueError(
            f"License server returned HTTP {error.code}: {code}") from error


def generate(output, build):
    # Fail before contacting the server if the destination already exists.
    if os.path.lexists(output):
        raise FileExistsError(f"Output already exists: {output}")
    if not output.parent.is_dir():
        raise ValueError(f"Output directory does not exist: {output.parent}")
    hashes = machine_hashes()
    data = request_evaluation(build, hashes)
    result = verify(data, hashes)
    if result["expired"]:
        raise ValueError("Server returned an expired evaluation; nothing saved")
    # O_EXCL also prevents overwriting a file created while requesting.
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
    except OSError:
        output.unlink()
        raise
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    request = commands.add_parser("request", help="Request an official evaluation")
    request.add_argument("--output", type=Path, required=True,
                         help="New file to save; existing files are never overwritten")
    request.add_argument("--build", type=int, default=261056,
                         help="Installed SmartGit 26.1 build (default: %(default)s)")
    check = commands.add_parser("verify", help="Verify a local credential offline")
    check.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "request":
            if args.build <= 0:
                raise ValueError("Build must be positive")
            result = generate(args.output, args.build)
            result["saved_to"] = str(args.output)
        else:
            result = verify(args.file.read_bytes(), machine_hashes())
        print(json.dumps(result, indent=2))
        return 2 if result["expired"] else 0
    except (OSError, ValueError, KeyError, urllib.error.URLError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
