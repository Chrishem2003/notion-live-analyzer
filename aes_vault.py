
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from modules.database import log_backend_event

def generate_aes_key() -> str:
    """Generates a secure 256-bit AES key encoded in base64."""
    key = AESGCM.generate_key(bit_length=256)
    return base64.b64encode(key).decode('utf-8')

def encrypt_vault_record(plaintext: str, base64_key: str) -> dict:
    """
    Encrypts sensitive academic or research records using AES-256-GCM with a unique nonce.
    """
    try:
        key = base64.b64decode(base64_key.encode('utf-8'))
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        
        log_backend_event("INFO", "Successfully encrypted secure vault record via AES-256-GCM.")
        return {
            "status": "success",
            "ciphertext": base64.b64encode(ciphertext).decode('utf-8'),
            "nonce": base64.b64encode(nonce).decode('utf-8')
        }
    except Exception as e:
        log_backend_event("ERROR", f"AES-256-GCM encryption failure: {str(e)}")
        return {"status": "error", "message": str(e)}

def decrypt_vault_record(b64_ciphertext: str, b64_nonce: str, base64_key: str) -> str:
    """
    Decrypts an AES-256-GCM encrypted vault record using its unique nonce and key.
    """
    try:
        key = base64.b64decode(base64_key.encode('utf-8'))
        aesgcm = AESGCM(key)
        ciphertext = base64.b64decode(b64_ciphertext.encode('utf-8'))
        nonce = base64.b64decode(b64_nonce.encode('utf-8'))
        
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode('utf-8')
    except Exception as e:
        log_backend_event("ERROR", f"AES-256-GCM decryption failure: {str(e)}")
        return ""

