import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from passlib.context import CryptContext
from dotenv import load_dotenv
import uvicorn

from .models import Base, User, Message, Purchase, PurchaseStatus
from .email import generate_otp, send_otp_email
from .payment import request_payment, verify_payment

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apps.rates_fetcher import fetch_live_rates

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 15 
    },
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

is_manual_mode = False

scheduler = AsyncIOScheduler()

pending_users = {}
OTP_LIFETIME_MINUTES = 5

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


async def update_system_rates():
    global rates

    if is_manual_mode:
        print("[SCHEDULER] Manual mode active — skipping auto-fetch.")
        return

    print("[SCHEDULER] Triggered! Fetching live rates from international API...")
    try:
        new_rates = await fetch_live_rates(fallback_rates=rates)
        if new_rates:
            rates["dollar"] = new_rates["dollar"]
            rates["euro"] = new_rates["euro"]
            rates["pound"] = new_rates["pound"]
            print(f"[SCHEDULER] SUCCESS! Rates in memory updated: {rates}")
        else:
            print("[SCHEDULER] WARNING: API returned empty data. Keeping previous rates.")
    except Exception as e:
        print(f"[SCHEDULER] ERROR: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.is_admin == True).first():
            db.add(User(
                username="admin",
                email="admin@gmail.com",
                password=hash_password("adminpassword"),
                is_admin=True,
            ))
            db.commit()
    finally:
        db.close()

    print("[LIFESPAN] Activating live currency fetcher...")
    try:
        await update_system_rates()
        scheduler.add_job(update_system_rates, "interval", hours=2)
        scheduler.start()
        print("[LIFESPAN] Scheduler started — refreshing every 2 hours.")
    except Exception as e:
        print(f"[LIFESPAN ERROR] Failed to start scheduler: {e}")

    yield

    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("[LIFESPAN] Scheduler stopped.")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

rates: dict[str, float] = {"dollar": 33.50, "euro": 36.20, "pound": 42.10}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request, db: Session) -> User | None:
    user_id = request.cookies.get("user_id")
    if not user_id:
        return None
    try:
        return db.get(User, int(user_id))
    except (ValueError, TypeError):
        return None


@app.get("/", response_class=HTMLResponse)
async def read_intro(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    template_context = {
        "success": True if user else False
    }
    return templates.TemplateResponse(
        request,
        "intro.html",
        template_context
    )    


@app.get("/signup", response_class=HTMLResponse)
def read_signup(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return RedirectResponse("/home", status_code=302)
    return templates.TemplateResponse(request , "signup.html")


@app.get("/login", response_class=HTMLResponse)
def read_login(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return RedirectResponse("/home", status_code=302)
    return templates.TemplateResponse(request , "login.html")


@app.get("/profile", response_class=HTMLResponse)
def read_profile(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(request , "profile.html", {"user": user})


@app.get("/communicate", response_class=HTMLResponse)
def read_communicate(request: Request):
    return templates.TemplateResponse(request , "communicate.html")


@app.get("/contact", response_class=HTMLResponse)
def read_contact(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    users = db.query(User).filter(User.id != user.id).all()
    return templates.TemplateResponse(request , "contact.html", {"users": users})


@app.get("/chat", response_class=HTMLResponse)
def read_chat(
    request: Request,
    db: Session = Depends(get_db),
    receiver_id: int = Query(...),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    receiver_user = db.query(User).filter(User.id == receiver_id).first()
    if not receiver_user:
        raise HTTPException(status_code=404, detail="User not found")
    messages = (
        db.query(Message)
        .filter(
            ((Message.sender_id == user.id) & (Message.receiver_id == receiver_user.id))
            | ((Message.sender_id == receiver_user.id) & (Message.receiver_id == user.id))
        )
        .order_by(Message.id.asc())
        .all()
    )
    return templates.TemplateResponse(
        request,
        "chat.html",
        {
            "messages": messages,
            "user": user,
            "receiver_user": receiver_user,
        },
    )


@app.get("/admin", response_class=HTMLResponse)
def read_admin(request: Request, db: Session = Depends(get_db)):
    admin = get_current_user(request, db)
    if not admin or not admin.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")

    all_purchases = db.query(Purchase).order_by(Purchase.id.desc()).all()
    successful = [p for p in all_purchases if p.status == PurchaseStatus.SUCCESS]

    return templates.TemplateResponse(
        request,
        "admin.html",
        {
            "rates": rates,
            "is_manual_mode": is_manual_mode,
            "purchases": all_purchases,
            "total_transactions": len(all_purchases),
            "total_sales_lira": round(sum(p.amount_lira for p in successful), 2),
            "crypto_stats": {
                "dollar": sum(p.count for p in successful if p.currency == "dollar"),
                "euro": sum(p.count for p in successful if p.currency == "euro"),
                "pound": sum(p.count for p in successful if p.currency == "pound"),
            },
        },
    )


@app.get("/home", response_class=HTMLResponse)
def read_home(request: Request, db: Session = Depends(get_db)):
    global rates
    
    if not rates["dollar"] or not rates["euro"] or not rates["pound"]:
        raise HTTPException(status_code=503, detail="Rates not configured yet.")
    
    dollar_obj = type("R", (), {"cost": rates["dollar"], "value": rates["dollar"]})()
    euro_obj   = type("R", (), {"cost": rates["euro"], "value": rates["euro"]})()
    pound_obj  = type("R", (), {"cost": rates["pound"], "value": rates["pound"]})()
    
    print(f"[ROUTE DEBUG] Sending to frontend -> Dollar: {rates['dollar']} TRY, Euro: {rates['euro']} TRY, Pound: {rates['pound']} TRY")
    
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "dollar": dollar_obj,
            "euro": euro_obj,
            "pound": pound_obj,
            "rates": rates 
        },
    )


@app.get("/sale/{currency_name}", response_class=HTMLResponse)
async def get_sale_page(currency_name: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if currency_name not in rates:
        raise HTTPException(status_code=404, detail="Currency not supported")
    return templates.TemplateResponse(
        request,
        "sale.html",
        {"name": currency_name, "rate": rates[currency_name]},
    )


@app.get("/payment/verify-callback", response_class=HTMLResponse)
async def bank_callback_verifier(
    request: Request,
    merchant_oid: str = Query(None, alias="merchant_oid"), 
    db: Session = Depends(get_db),
):
    if not merchant_oid:
        merchant_oid = request.query_params.get("merchant_oid", "")

    purchase = db.query(Purchase).filter(Purchase.authority == merchant_oid).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Transaction reference not found.")

    verification = await verify_payment(
        amount_lira=purchase.amount_lira, merchant_oid=merchant_oid
    )
    
    if verification["success"] and verification["status"] == "verified":
        purchase.status = PurchaseStatus.SUCCESS
        purchase.authority = str(verification["ref_id"])
        db.commit()
        return templates.TemplateResponse(
            request,
            "bankinfo.html",
            {
                "status": "success",
                "ref_id": verification["ref_id"],
                "amount": purchase.amount_lira,
                "currency_count": purchase.count,
                "currency_type": purchase.currency,
            },
        )

    purchase.status = PurchaseStatus.FAILED
    db.commit()
    return templates.TemplateResponse(
        request,
        "bankinfo.html",
        {
            "status": "failed",
            "message": "Transaction was canceled or failed at European network terminal.",
        },
    )


@app.post("/signup")
async def signup(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    if db.query(User).filter(User.username == username).first():
        return JSONResponse(
            status_code=409,
            content={"success": False, "message": "Username already exists"},
        )
    if db.query(User).filter(User.email == email).first():
        return JSONResponse(
            status_code=409,
            content={"success": False, "message": "Email already registered"},
        )
    
    otp = generate_otp()
    pending_users[email] = {
        "username": username,
        "email": email,
        "password": hash_password(password),
        "otp": otp,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=OTP_LIFETIME_MINUTES),
    }
    
    await send_otp_email(email, otp)
    
    return JSONResponse(
        content={"success": True, "message": f"Verification code sent to {email}"}
    )

@app.post("/verify")
async def verify(  
    email: str = Form(...),
    otpCode: str = Form(...),
    db: Session = Depends(get_db),
):
    entry = pending_users.get(email)
    if not entry:
        return JSONResponse(
            status_code=200,  
            content={"success": False, "message": "No pending signup found. Please start over."},
        )
        
    if datetime.now(timezone.utc) > entry["expires_at"]:
        if email in pending_users:
            del pending_users[email]
        return JSONResponse(
            status_code=200,
            content={
                "success": False,
                "message": f"Code expired ({OTP_LIFETIME_MINUTES} min limit). Please sign up again.",
            },
        )
        
    if entry["otp"] != otpCode.strip():
        return JSONResponse(
            status_code=200,
            content={"success": False, "message": "Incorrect code. Please try again."},
        )
        
    db.add(
        User(username=entry["username"], password=entry["password"], email=email)
    )
    db.commit()
    
    if email in pending_users:
        del pending_users[email]
        
    return JSONResponse(
        content={"success": True, "message": "Account created! Redirecting to login…"}
    )

@app.post("/login")
def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()
    if user and verify_password(password, user.password):
        response = JSONResponse(
            content={
                "success": True,
                "message": "Login successful",
                "is_admin": user.is_admin,
            }
        )
        response.set_cookie("user_id", str(user.id))
        return response
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"success": False, "message": "Invalid username or password"},
    )


@app.post("/logout")
def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("user_id")
    return response


@app.post("/chat")
def chat(
    request: Request,
    db: Session = Depends(get_db),
    receiverId: str = Form(...),
    text: str = Form(...),
):
    user = get_current_user(request, db)
    receiver = db.get(User, int(receiverId))
    if not user or not receiver:
        return JSONResponse(status_code=401, content={"success": False})
    new_message = Message(content=text, sender_id=user.id, receiver_id=receiver.id)
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    return JSONResponse(
        content={
            "success": True,
            "message": "Message sent",
            "message_id": new_message.id,
            "created_at": new_message.created_at.strftime("%H:%M"),
        }
    )


@app.post("/admin")
async def update_rates(
    action: str = Form("save"),
    dollar: float = Form(None),
    euro: float = Form(None),
    pound: float = Form(None),
):
    global rates, is_manual_mode

    if action == "auto":
        is_manual_mode = False
        await update_system_rates()
        return JSONResponse(content={"success": True, "message": "Switched to Automatic API mode. Rates refreshed."})

    elif action == "save":
        if not dollar or not euro or not pound:
            return JSONResponse(status_code=400, content={"success": False, "message": "All three rates are required."})
        is_manual_mode = True
        rates["dollar"] = dollar
        rates["euro"] = euro
        rates["pound"] = pound
        return JSONResponse(content={"success": True, "message": "Manual override applied successfully."})

    return JSONResponse(status_code=400, content={"success": False, "message": "Unknown action."})


@app.post("/sale/{currency_name}")
async def place_order_handler(
    currency_name: str,
    request: Request,
    value: float = Form(...),
    db: Session = Depends(get_db),
):
    if currency_name not in rates:
        return JSONResponse(content={"success": False, "message": "Unsupported currency"})

    user = get_current_user(request, db)
    if not user:
        return JSONResponse(
            content={"success": False, "message": "User session expired. Please re-login."},
            status_code=401,
        )

    rate = rates[currency_name]
    
    amount_lira = float(value * rate)

    if amount_lira < 5.0:
        return JSONResponse(
            content={"success": False, "message": "Minimum transaction is 5.00 TRY."}
        )

    callback_url = os.getenv("PAYMENT_CALLBACK_URL", "http://127.0.0.1:8000/payment/verify-callback")
    description = f"Purchase of {value} {currency_name} from Royal Exchange"

    payment_res = await request_payment(
        amount_lira=amount_lira,
        description=description,
        callback_url=callback_url,
        email=user.email,
    )

    if payment_res["success"]:
        purchase_record = Purchase(
            count=value,
            currency=currency_name,
            amount_lira=amount_lira,
            status=PurchaseStatus.PENDING,
            authority=payment_res["authority"], 
            buyer_id=user.id,
        )
        db.add(purchase_record)
        db.commit()
        return JSONResponse(
            content={"success": True, "redirect_url": payment_res["payment_url"]}
        )
    else:
        return JSONResponse(
            content={"success": False, "message": "Could not initiate PayTR international gateway session."},
            status_code=500,
        )


if __name__ == "__main__":
    uvicorn.run("apps.main:app", host="127.0.0.1", port=8000, reload=True)