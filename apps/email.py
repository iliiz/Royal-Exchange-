import os
import httpx
import random

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "zrkiliya@gmail.com")

def generate_otp() -> str:
    return str(random.randint(1000, 9999))

async def send_otp_email(receiver_email: str, otp_code: str) -> bool:
    url = "https://api.brevo.com/v3/smtp/email"
    
    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }
    
    html_body = f"""
    <html>
        <body style="background-color: #030014; color: #f0f0f0; font-family: sans-serif; padding: 30px; text-align: center;">
            <div style="max-width: 500px; margin: 0 auto; background: rgba(18, 15, 36, 0.6); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 20px; padding: 20px; backdrop-filter: blur(10px);">
                <h1 style="color: #bc95ff; margin-bottom: 5px; font-weight: 700; tracking-content: wider;">Exchange Royal</h1>
                <p style="color: rgba(255,255,255,0.4); font-size: 0.8rem; margin-top: 0;">Terminal Registration Desk</p>
                
                <p style="font-size: 1rem; color: #cbd5e1; margin-top: 25px;">Thank you for creating an account. Use the secure activation code below to verify your session:</p>
                
                <div style="background-color: rgba(99, 68, 245, 0.1); border: 1px solid rgba(99, 68, 245, 0.2); display: inline-block; padding: 12px 35px; border-radius: 12px; font-size: 2.2rem; font-weight: bold; color: #a78bfa; letter-spacing: 6px; margin: 20px 0; font-family: monospace;">
                    {otp_code}
                </div>
                
                <p style="color: rgba(255,255,255,0.3); font-size: 0.75rem; margin-top: 20px;">This security token is strictly confidential and will expire in 5 minutes.</p>
            </div>
        </body>
    </html>
    """
    
    payload = {
        "sender": {"name": "Royal Exchange Support", "email": SENDER_EMAIL},
        "to": [{"email": receiver_email}],
        "subject": "Verification Code - Royal Terminal",
        "htmlContent": html_body
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code in [200, 201, 202]:
                print(f"[BREVO API] Security token successfully delivered to {receiver_email}")
                return True
            else:
                print(f"[BREVO ERROR] API Rejected request: {response.text}")
                return False
    except Exception as e:
        print(f"[EMAIL SYSTEM ERROR] Exception caught during transport: {e}")
        return False
