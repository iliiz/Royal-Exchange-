import os
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("ExchangeRoyal.RatesFetcher")

EXCHANGERATE_API_KEY = os.getenv("EXCHANGERATE_API_KEY", "")

EXCHANGERATE_URL = f"https://v6.exchangerate-api.com/v6/{EXCHANGERATE_API_KEY}/latest/TRY"


async def fetch_live_rates(fallback_rates: dict) -> dict:
    if not EXCHANGERATE_API_KEY:
        print("[FETCHER] EXCHANGERATE_API_KEY missing — cannot fetch international rates.")
        return fallback_rates

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                EXCHANGERATE_URL,
                headers={"User-Agent": "ExchangeRoyal/1.0"},
            )
            data = r.json()
            
            if r.status_code == 200 and data.get("result") == "success":
                conversion_rates = data.get("conversion_rates", {})
                try_to_usd = conversion_rates.get("USD")
                try_to_eur = conversion_rates.get("EUR")
                try_to_gbp = conversion_rates.get("GBP")
                
                result = {}
                
                if try_to_usd and try_to_usd > 0:
                    result["dollar"] = round(1 / try_to_usd, 4)
                    print(f"[FETCHER] Live Dollar rate: {result['dollar']} TRY")
                else:
                    result["dollar"] = fallback_rates.get("dollar")

                if try_to_eur and try_to_eur > 0:
                    result["euro"] = round(1 / try_to_eur, 4)
                    print(f"[FETCHER] Live Euro rate: {result['euro']} TRY")
                else:
                    result["euro"] = fallback_rates.get("euro")

                if try_to_gbp and try_to_gbp > 0:
                    result["pound"] = round(1 / try_to_gbp, 4)
                    print(f"[FETCHER] Live Pound rate: {result['pound']} TRY")
                else:
                    result["pound"] = fallback_rates.get("pound")

                return result
                
            else:
                print(f"[FETCHER] exchangerate-api error: {data.get('error-type', 'Unknown')}")
                return fallback_rates
                
    except Exception as e:
        print(f"[FETCHER] Error fetching international cross rates: {e}")
        return fallback_rates