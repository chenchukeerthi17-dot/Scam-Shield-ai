
from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma3:1b"


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/scan", methods=["POST"])
def scan():
    try:
        data = request.get_json(silent=True) or {}
        message = data.get("message", "").strip()

        if not message:
            return jsonify({
                "result": "Please enter a message to scan."
            }), 400

        message_lower = message.lower()

        # Basic warning-sign checks
        high_risk_phrases = [
            "share your otp",
            "send your otp",
            "tell me your otp",
            "share your password",
            "send your password",
            "enter your otp",
            "enter your password",
            "bank account will be blocked",
            "account will be blocked today",
            "urgent payment"
        ]

        medium_risk_phrases = [
            "you won a free prize",
            "claim your reward",
            "click this link immediately",
            "limited time offer",
            "you have won a prize"
        ]

        if any(phrase in message_lower
               for phrase in high_risk_phrases):
            return jsonify({
                "result": (
                    "Risk Level: HIGH\n"
                    "Reason: This message contains a request "
                    "for sensitive information or urgent payment.\n"
                    "Advice: Do not share OTPs, passwords, "
                    "or banking details. Verify through official channels."
                )
            })

        prompt = f"""
You are Scam Shield AI, a scam detection assistant.

Analyze the message for possible fraud, phishing,
impersonation, suspicious links, and manipulation.

Classify the risk as HIGH, MEDIUM, or LOW.

HIGH: Clear requests for passwords, OTPs, banking
details, suspicious payments, or strong scam indicators.

MEDIUM: Suspicious offers, unusual requests, or
messages that need more context.

LOW: No clear scam indicators. Do not guarantee safety.

Return exactly this format:
Risk Level: HIGH, MEDIUM, or LOW
Reason: Explain the warning signs.
Advice: Give safe next steps.

Message:
{message}
"""

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False
            },
            timeout=90
        )

        response.raise_for_status()
        result = response.json()["response"]

        # Add a warning for common suspicious offers
        if any(phrase in message_lower
               for phrase in medium_risk_phrases):
            if "risk level: low" in result.lower():
                result = (
                    "Risk Level: MEDIUM\n"
                    "Reason: The message uses a prize or urgent "
                    "link claim that may be deceptive.\n"
                    "Advice: Do not click unknown links. Verify "
                    "the offer using the official website."
                )

        return jsonify({"result": result})

    except requests.exceptions.ConnectionError:
        return jsonify({
            "result": (
                "Could not connect to Ollama. "
                "Make sure Ollama is running on your computer."
            )
        }), 503

    except requests.exceptions.Timeout:
        return jsonify({
            "result": "The AI took too long to respond. Please try again."
        }), 504

    except requests.exceptions.RequestException as error:
        return jsonify({
            "result": f"AI request failed: {error}"
        }), 502

    except Exception as error:
        app.logger.exception("Scan failed")
        return jsonify({
            "result": f"Unexpected error: {error}"
        }), 500


if __name__ == "__main__":
    app.run(debug=False, port=5000)
