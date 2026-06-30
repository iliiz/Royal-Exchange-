# Exchange Royal ✦ 

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F20?style=for-the-badge&logo=python&logoColor=white)](https://www.sqlalchemy.org)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-06B6D4?style=for-the-badge&logo=Tailwind-CSS&logoColor=white)](https://tailwindcss.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

> **Live Demo:** [Deploying Soon / View Live Application](http://127.0.0.1:8000) *(Update this link once hosted on your domain or cloud provider)*

**Exchange Royal** is a sophisticated, full-stack currency exchange platform meticulously engineered for speed, security, and an exceptional user experience. Built using a modern asynchronous Python architecture, this terminal bridges international payment gateways with real-time financial metrics, wrapped inside an immersive, high-end visual environment. It serves as a definitive proof-of-concept for secure, high-concurrency Fintech applications.

---

## 🚀 Core Architecture & Technical Highlights

* **Asynchronous Engine & FastAPI:** Driven by FastAPI and powered by an **Event-Driven Lifespan**, the application maintains zero-blocking I/O. By utilizing `httpx` and `AsyncIOScheduler`, the backend effortlessly processes concurrent operations without degrading server response times.
* **Robust Database Management (SQLAlchemy ORM):** Built with an enterprise-grade relational database schema. It manages complex entity-relationship mappings between users, secure purchase ledgers, and encrypted communication logs, ensuring strict transactional data integrity.
* **Automated, Real-Time Market Syncing:** Features an automated background worker that polls international financial APIs every few hours to update cross-rates against the Turkish Lira (TRY) for USD, EUR, and GBP. It includes an intelligent **Plan-B Fallback System** to preserve system operationality during upstream API outages.
* **Secure Payment Gateway Integration (PayTR API):** Integrated with the international PayTR payment infrastructure. The system securely prepares payloads, masks floating-point discrepancies by processing amounts in sub-units (Kuruş), handles dynamic sub-arrays for shopping baskets, and relies on strict custom callback endpoints to verify successful settlement.

---

## 🛡️ Security, Networking & Middleware

* **HMAC-SHA256 & Base64 Cryptographic Ledger:** Financial data integrity is guaranteed through advanced cryptography. Transactions are secured using Hash-based Message Authentication Codes (`HMAC-SHA256`) and client-side payload signatures to completely neutralize mid-transit data manipulation (Man-in-the-Middle attacks).
* **Encrypted Authentication & Session Guarding:** User onboarding is protected via `passlib` bcrypt password hashing, paired with a temporary, non-blocking asynchronous email OTP (One-Time Password) verification system via the Brevo SMTP API. Session cookies are dynamically managed to authorize access controls.
* **Granular Multi-Tier Access Control:** Built-in segregation of roles via dedicated user states and a comprehensive Administrative Dashboard. Administrators can monitor real-time gross volume statistics, track isolated asset flows, and manage manual vs. automatic pricing overrides.

---

## 🎨 Immersive Frontend & Client Features

* **Encrypted P2P Chat Sandbox:** Features a dedicated internal communication suite, allowing authenticated users to exchange messages securely with indexed, chronological relational data binding.
* **Ultra-Modern "Glassmorphism" Design Language:** The front-end leverages a striking, cyberpunk-inspired visual identity. Utilizing custom, dark-ambient glowing aesthetic gradients and dynamic fluid backgrounds, the user interface remains highly responsive and premium across all screen sizes.
* **Scannable Invoice Data Rendering:** Powered by Jinja2 server-side rendering templating, invoice cards (`bankinfo.html`) and administrative panels dynamically format complex localized currency floats up to two decimal places for crisp user transparency.

---

## 🛠️ Tech Stack & Dependencies

### Backend Ecosystem
* **Core:** Python 3.12+, FastAPI, Starlette, Uvicorn
* **Database & ORM:** SQLAlchemy, SQLite (Development) / PostgreSQL (Production)
* **Task Scheduling:** APScheduler (AsyncIOScheduler)
* **HTTP Client:** HTTPX (Asynchronous Requests)

### Security & Encryption
* **Signatures & Hashing:** HMAC, Hashlib, Passlib (Bcrypt)
* **Environment Configuration:** Python-Dotenv

### Frontend Framework
* **Templating Engine:** Jinja2
* **Styling Architecture:** TailwindCSS, Custom Fluid CSS Utilities

---

## 📦 Local Installation & Setup

Follow these steps to spin up the development environment locally:

1. **Clone the Repository:**
   ```bash
   git clone [https://github.com/yourusername/ExchangeRoyal.git](https://github.com/yourusername/ExchangeRoyal.git)
   cd ExchangeRoyal
