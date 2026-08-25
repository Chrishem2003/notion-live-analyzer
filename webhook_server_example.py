"""
webhook_server_example.py
Streamlit apps only handle browser requests — they can't receive Stripe's
server-to-server webhook POSTs. This is a tiny separate Flask process that
does, and flips a subscription to 'active' on successful payment.

Run alongside the Streamlit app:
    D:\\ChrishemHub\\venv\\Scripts\\python.exe webhook_server_example.py

Point your Stripe webhook endpoint (in the Stripe Dashboard) at:
    http://<your-server>:4242/stripe-webhook
"""

from flask import Flask, request
from modules import billing_stripe, subscription

app = Flask(__name__)


@app.route("/stripe-webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature", "")
    try:
        event = billing_stripe.handle_webhook_event(payload, sig_header)
    except Exception as e:
        return {"error": str(e)}, 400

    if event["type"] in ("checkout.session.completed", "invoice.paid"):
        email = event["data"]["object"].get("customer_email") or event["data"]["object"].get("customer_details", {}).get("email")
        if email:
            conn = subscription.get_conn()
            conn.execute(
                "INSERT INTO subscriptions (email, trial_started, plan) VALUES (?,?,?) "
                "ON CONFLICT(email) DO UPDATE SET plan='active'",
                (email.lower(), __import__("datetime").datetime.utcnow().isoformat(), "active"),
            )
            conn.commit()
            conn.close()

    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(port=4242)
