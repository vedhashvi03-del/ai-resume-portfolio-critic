# 📄 AI Resume & Portfolio Critic 

A freemium web app that gives job seekers instant, AI-powered feedback on their resume and portfolio.
Built for the **PayPal AI Hackathon** with **Streamlit**, **Google Gemini** and the **PayPal Sandbox**.

- **Free tier:** 3 quick, personalised tips.
- **Premium tier ($4.99, PayPal Sandbox):** a full expert critique with an overall score, strengths, weaknesses, before/after bullet rewrites, ATS keyword gaps, portfolio feedback and a 30-day action plan.

## How PayPal is used

1. The sidebar shows the **PayPal Smart Buttons** (JavaScript SDK). The buyer pays $4.99 in the Sandbox.
2. After the payment is captured, the button shows an **Order ID**.
3. The user pastes the Order ID into the app and clicks **Verify payment**.
4. The Python backend gets an OAuth token and calls PayPal's **Orders API** (`GET /v2/checkout/orders/{id}`). Premium unlocks **only if** PayPal reports the order as `COMPLETED`, in `USD`, for at least the premium price.

Because the unlock decision is made by PayPal's servers and not by the browser, the paywall can't be bypassed by editing the page.
The premium prompt is never sent to the AI until payment is verified.

## Tech stack

Python, Streamlit, Google Gemini API (`google-genai`), PayPal JavaScript SDK + Orders REST API, pypdf, BeautifulSoup.

## Quick start

**Requirements:** Python 3.10+

```bash
git clone <YOUR-REPO-URL>
cd <YOUR-REPO-FOLDER>
python -m pip install -r requirements.txt
```

Create the secrets file:

1. Make a folder named `.streamlit`.
2. Copy `secrets.toml.example` into it and rename the copy to `secrets.toml`.
3. Fill in your own keys:

```toml
GEMINI_API_KEY = "..."        # free: https://aistudio.google.com/app/apikey
PAYPAL_CLIENT_ID = "..."      # https://developer.paypal.com > Apps & Credentials > Sandbox
PAYPAL_SECRET = "..."
```

Run:

```bash
python -m streamlit run app.py
```

The app opens at http://localhost:8501.

### Creating the PayPal Sandbox keys

1. Log in at https://developer.paypal.com and make sure **Sandbox** is selected.
2. **Testing Tools → Sandbox Accounts:** create a **Business** account and a **Personal** (buyer) account, both with country **United States**.
3. **Apps & Credentials → Create App** (type *Merchant*), choosing the US Business account as its sandbox account.
4. Copy the app's **Client ID** and **Secret** into `secrets.toml`.

## 🧪 Testing instructions for judges

1. Start the app (see above), or open the hosted demo: **<HOSTED-DEMO-URL-IF-ANY>**
2. Paste any resume text (or upload a PDF) and click **Get my 3 free tips**. You get 3 tips.
3. In the sidebar, click the yellow **PayPal** button and log in with this **Sandbox buyer** account (fake money only):
   - Email: `<FILL-IN-SANDBOX-BUYER-EMAIL>`
   - Password: `<FILL-IN-SANDBOX-BUYER-PASSWORD>`
4. Approve the $4.99 payment. A green "Payment successful" message with an **Order ID** appears. Click the box to copy it.
5. Paste the Order ID into **"Paste your PayPal Order ID here"** and click **Verify payment**.
6. The sidebar shows **Premium unlocked 🎉**. Click **Get my full premium critique** to see the full report.

> If you run the app locally you need your own Gemini key and PayPal Sandbox app keys (steps above). No real money is ever charged.

## Project structure

```
app.py                  # the whole Streamlit app
requirements.txt
secrets.toml.example    # template for .streamlit/secrets.toml (real file is git-ignored)
LICENSE                 # MIT
```

## Known limitations

- Premium status lasts for the current browser session only (refreshing resets it). A production version would store purchases in a database tied to user accounts.
- The Order ID is pasted manually because Streamlit can't receive JavaScript callbacks from the PayPal iframe without a custom component. A custom component or webhook would make unlocking automatic.
- Sandbox only. Going live requires live PayPal credentials and swapping the API base URL.

## License

MIT, see [LICENSE](LICENSE).
