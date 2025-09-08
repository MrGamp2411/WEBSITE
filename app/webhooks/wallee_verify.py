import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature
from app.wallee_client import whenc_srv


def parse_signature_header(header: str):
    """
    Atteso: algorithm=SHA256withECDSA, keyId=<id>, signature=<base64>
    """
    if not header:
        raise ValueError("Missing x-signature header")
    parts = [p.strip() for p in header.split(",")]
    kv = {}
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            kv[k.strip()] = v.strip()
    algo = kv.get("algorithm")
    key_id = kv.get("keyId")
    sig64 = kv.get("signature")
    if algo != "SHA256withECDSA" or not key_id or not sig64:
        raise ValueError("Invalid x-signature header")
    try:
        sig = base64.b64decode(sig64, validate=True)
    except Exception:
        raise ValueError("Invalid signature base64")
    return key_id, sig


def get_public_key_obj(key_id: str):
    # alcune versioni accettano int, altre str: prova entrambe
    try:
        resp = whenc_srv.read(int(key_id))
    except Exception:
        resp = whenc_srv.read(key_id)

    pub_b64 = getattr(resp, "public_key", None) or getattr(resp, "publicKey", None)
    if not pub_b64:
        raise ValueError("Missing public key from Wallee")

    try:
        pub_der = base64.b64decode(pub_b64, validate=True)
    except Exception:
        raise ValueError("Invalid public key base64 from Wallee")

    try:
        return serialization.load_der_public_key(pub_der)
    except Exception as e:
        raise ValueError(f"Unable to load DER public key: {e}")


def verify_signature_bytes(raw_body: bytes, header: str):
    key_id, signature = parse_signature_header(header)
    public_key = get_public_key_obj(key_id)
    try:
        public_key.verify(signature, raw_body, ec.ECDSA(hashes.SHA256()))
    except InvalidSignature:
        raise ValueError("Invalid webhook signature")
