"""
AI Resume & Portfolio Critic (Freemium)
- Free tier: 3 basic tips
- Premium tier: full in-depth critique, unlocked after a PayPal Sandbox payment

Run with:  python -m streamlit run app.py
"""

import os
import time

import requests
import streamlit as st
import streamlit.components.v1 as components
from bs4 import BeautifulSoup
from google import genai
from pypdf import PdfReader


# ============================================================
# 1. KEYS (loaded from .streamlit/secrets.toml or environment variables)
#    Never type your real keys into this file.
# ============================================================
def get_secret(name: str) -> str:
    try:
        return st.secrets[name]
    except Exception:
        return os.environ.get(name, "")


GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
PAYPAL_CLIENT_ID = get_secret("PAYPAL_CLIENT_ID")
PAYPAL_SECRET = get_secret("PAYPAL_SECRET")

GEMINI_MODEL = "gemini-3.8-flash"  # if Google retires this name, swap in a newer Flash model
PREMIUM_PRICE = "4.99"
CURRENCY = "USD"
PAYPAL_API = "https://api-m.sandbox.paypal.com"  # sandbox (fake money) endpoint

# ============================================================
# 2. PAGE SETUP
# ============================================================
st.set_page_config(page_title="AI Resume & Portfolio Critic", page_icon="📄", layout="wide")

if "is_premium" not in st.session_state:
    st.session_state.is_premium = False


# ============================================================
# 3. HELPER FUNCTIONS
# ============================================================
def read_pdf(uploaded_file) -> str:
    reader = PdfReader(uploaded_file)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def read_portfolio(url: str) -> str:
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        text = " ".join(soup.get_text(separator=" ").split())
        return text[:6000]
    except Exception as e:
        return f"(Could not load portfolio: {e})"


def ask_gemini(prompt: str) -> str:
    client = genai.Client(api_key=GEMINI_API_KEY)

    # Build a list of models to try: your preferred one first, then other Flash models
    try:
        names = [
            m.name.replace("models/", "")
            for m in client.models.list()
            if "generateContent" in (m.supported_actions or [])
        ]
    except Exception:
        names = []
    fallbacks = [n for n in names if "flash" in n and "image" not in n and n != GEMINI_MODEL]
    models_to_try = [GEMINI_MODEL] + fallbacks[:3]

    last_error = None
    for model in models_to_try:
        for attempt in range(3):
            try:
                response = client.models.generate_content(model=model, contents=prompt)
                return response.text
            except Exception as e:
                last_error = e
                msg = str(e)
                if "503" in msg or "429" in msg or "UNAVAILABLE" in msg:
                    time.sleep(2 * (attempt + 1))  # wait 2s, 4s, 6s then retry
                    continue
                break  # a different error (like 404): move on to the next model
    raise last_error


def build_prompt(resume: str, portfolio: str, target_role: str, premium: bool) -> str:
    material = f"TARGET ROLE: {target_role or 'Not specified'}\n\nRESUME:\n{resume}"
    if portfolio:
        material += f"\n\nPORTFOLIO WEBSITE CONTENT:\n{portfolio}"

    if not premium:
        return (
            "You are a friendly career coach. Give EXACTLY 3 short, basic tips "
            "to improve this resume/portfolio. Number them 1-3, one or two sentences each. "
            "Do not give anything else.\n\n" + material
        )

    return (
        "You are an expert recruiter and career coach. Give a thorough, honest critique in Markdown "
        "with these sections:\n"
        "## Overall Score (out of 100, with a one-line justification)\n"
        "## Strengths\n"
        "## Critical Weaknesses\n"
        "## Line-by-Line Rewrites (show 'Before' and 'After' for at least 5 weak bullets, "
        "using strong verbs and measurable results)\n"
        "## ATS Keyword Gaps (for the target role)\n"
        "## Portfolio Feedback (if portfolio content is provided)\n"
        "## 30-Day Action Plan\n\n" + material
    )


def get_paypal_token() -> str:
    r = requests.post(
        f"{PAYPAL_API}/v1/oauth2/token",
        auth=(PAYPAL_CLIENT_ID, PAYPAL_SECRET),
        data={"grant_type": "client_credentials"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def verify_paypal_order(order_id: str) -> bool:
    """Asks PayPal's servers whether this order was really paid. Can't be faked."""
    try:
        token = get_paypal_token()
        r = requests.get(
            f"{PAYPAL_API}/v2/checkout/orders/{order_id.strip()}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if r.status_code != 200:
            return False
        order = r.json()
        amount = order["purchase_units"][0]["amount"]
        return (
            order.get("status") == "COMPLETED"
            and amount.get("currency_code") == CURRENCY
            and float(amount.get("value", 0)) >= float(PREMIUM_PRICE)
        )
    except Exception:
        return False


def paypal_button_html() -> str:
    return f"""
    <div id="paypal-button-container"></div>
    <div id="result" style="font-family:sans-serif;margin-top:12px;"></div>
    <script src="https://www.paypal.com/sdk/js?client-id={PAYPAL_CLIENT_ID}&currency={CURRENCY}"></script>
    <script>
      paypal.Buttons({{
        createOrder: function(data, actions) {{
          return actions.order.create({{
            purchase_units: [{{
              description: "Resume Critic Premium",
              amount: {{ currency_code: "{CURRENCY}", value: "{PREMIUM_PRICE}" }}
            }}]
          }});
        }},
        onApprove: function(data, actions) {{
          return actions.order.capture().then(function(details) {{
            document.getElementById("result").innerHTML =
              "<b style='color:green'>✅ Payment successful!</b><br>" +
              "Copy your Order ID and paste it into the box below the button:<br>" +
              "<input id='oid' readonly style='width:260px;padding:6px;margin-top:6px;' value='" + details.id + "' " +
              "onclick='this.select();document.execCommand(\\"copy\\");'>" +
              "<br><small>(click the box to copy)</small>";
          }});
        }},
        onError: function(err) {{
          document.getElementById("result").innerHTML =
            "<span style='color:red'>Payment error. Please try again.</span>";
        }}
      }}).render("#paypal-button-container");
    </script>
    """


# ============================================================
# 4. SIDEBAR: UPGRADE / PAYMENT
# ============================================================
with st.sidebar:
    st.header("⭐ Premium")
    if st.session_state.is_premium:
        st.success("Premium unlocked! 🎉")
    elif not (PAYPAL_CLIENT_ID and PAYPAL_SECRET):
        st.warning("PayPal keys are missing. Add PAYPAL_CLIENT_ID and PAYPAL_SECRET "
                   "to .streamlit/secrets.toml (see README).")
    else:
        st.write(f"Unlock the **full critique** (score, rewrites, ATS keywords, action plan) "
                 f"for **${PREMIUM_PRICE}**.")
        st.caption("Sandbox mode: use a PayPal *sandbox buyer* account. No real money is charged.")
        components.html(paypal_button_html(), height=420, scrolling=True)

        order_id = st.text_input("Paste your PayPal Order ID here after paying")
        if st.button("Verify payment"):
            if not order_id.strip():
                st.warning("Please paste your Order ID first.")
            elif verify_paypal_order(order_id):
                st.session_state.is_premium = True
                st.rerun()
            else:
                st.error("Couldn't verify that payment. Check the Order ID and try again.")

# ============================================================
# 5. MAIN PAGE
# ============================================================
st.title("📄 AI Resume & Portfolio Critic")
st.write("Get instant feedback on your resume. Free users get 3 quick tips; premium gets a full expert critique.")

target_role = st.text_input("Target job role (optional)", placeholder="e.g. Junior Data Analyst")

tab_paste, tab_pdf = st.tabs(["Paste resume text", "Upload PDF"])
resume_text = ""
with tab_paste:
    pasted = st.text_area("Paste your resume here", height=250)
with tab_pdf:
    pdf_file = st.file_uploader("Upload your resume (PDF)", type=["pdf"])

if pdf_file is not None:
    resume_text = read_pdf(pdf_file)
elif pasted:
    resume_text = pasted

portfolio_url = st.text_input("Portfolio website URL (optional)", placeholder="https://yourname.dev")

label = "Get my full premium critique" if st.session_state.is_premium else "Get my 3 free tips"
if st.button(label, type="primary"):
    if not GEMINI_API_KEY:
        st.error("Gemini API key is missing. Add GEMINI_API_KEY to .streamlit/secrets.toml (see README).")
    elif len(resume_text.strip()) < 50:
        st.warning("Please paste or upload a resume (at least a few lines).")
    else:
        with st.spinner("Analyzing..."):
            portfolio_text = read_portfolio(portfolio_url) if portfolio_url else ""
            try:
                prompt = build_prompt(resume_text, portfolio_text, target_role, st.session_state.is_premium)
                result = ask_gemini(prompt)
                st.subheader("Your feedback")
                st.markdown(result)
                if not st.session_state.is_premium:
                    st.info("🔒 Want the score, rewrites, ATS keywords and a 30-day plan? "
                            "Upgrade in the sidebar.")
            except Exception as e:
                st.error(f"Something went wrong calling the AI: {e}")
