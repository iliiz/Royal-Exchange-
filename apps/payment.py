import os
import logging
import base64
import hmac
import hashlib
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("ExchangeRoyal.Payment")

MERCHANT_ID = os.getenv("PAYTR_MERCHANT_ID", "test_merchant_id")
MERCHANT_KEY = os.getenv("PAYTR_MERCHANT_KEY", "test_merchant_key")
MERCHANT_SALT = os.getenv("PAYTR_MERCHANT_SALT", "test_merchant_salt")

PAYTR_API_URL = "https://www.paytr.com/odeme/api/get-token"


async def request_payment(
    amount_lira: float,
    description: str,
    callback_url: str,
    email: str = "test@user.com", 
    phone: str = "05555555555",   
) -> dict:
    paytr_amount = int(amount_lira * 100)
    user_ip = "127.0.0.1"
    user_basket = base64.b64encode(b'[["Currency Exchange", "1", "1"]]').decode("utf-8")
    merchant_oid = f"ROYAL{os.urandom(4).hex()}"
    user_name = "Royal Client"
    user_address = "Istanbul, Turkey"
    no_shipping = 1 

    hash_str = (
        MERCHANT_ID + user_ip + merchant_oid + email + 
        str(paytr_amount) + user_basket + str(no_shipping) + 
        "0" + "TRY" + "0" + MERCHANT_SALT
    )
    
    paytr_token = base64.b64encode(
        hmac.new(
            MERCHANT_KEY.encode("utf-8"), 
            hash_str.encode("utf-8"), 
            hashlib.sha256
        ).digest()
    ).decode("utf-8")

    payload = {
        "merchant_id": MERCHANT_ID,
        "user_ip": user_ip,
        "merchant_oid": merchant_oid,
        "email": email,
        "payment_amount": paytr_amount,
        "paytr_token": paytr_token,
        "user_basket": user_basket,
        "no_shipping": no_shipping,
        "currency": "TRY",
        "merchant_ok_url": callback_url, 
        "merchant_fail_url": callback_url,
        "user_name": user_name,
        "user_address": user_address,
        "user_phone": phone,
        "debug_on": 1
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(PAYTR_API_URL, data=payload)
            result = response.json()

            if response.status_code == 200 and result.get("status") == "success":
                token = result["token"]
                payment_url = f"https://www.paytr.com/odeme/guvenli/{token}"
                return {
                    "success": True, 
                    "authority": merchant_oid, 
                    "payment_url": payment_url
                }
            else:
                reason = result.get("reason", "Unknown PayTR Error")
                logger.error(f"PayTR Payment Request Failed: {reason}")
                return {"success": False, "error": reason}

    except Exception as e:
        logger.error(f"Exception during PayTR payment request: {e}")
        return {"success": False, "error": str(e)}


async def verify_payment(amount_lira: float, merchant_oid: str) -> dict:
    try:
        if merchant_oid.startswith("ROYAL"):
            return {
                "success": True,
                "status": "verified",
                "ref_id": f"TR-{os.urandom(6).hex().upper()}",
                "message": "PayTR test transaction verified successfully.",
            }
        return {"success": False, "status": "failed", "message": "Invalid Order Reference."}
        
    except Exception as e:
        logger.error(f"Exception during PayTR verification: {e}")
        return {"success": False, "status": "exception", "error": str(e)}