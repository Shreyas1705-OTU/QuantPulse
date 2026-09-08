"""
Thin wrapper around the Azure OpenAI chat-completions API.

Deliberately just plain functions, not a class -- ai/explainer.py and
ai/daily_summary.py each need exactly one kind of call (build a prompt,
get back plain text), nothing more. Client construction (build_client)
is separate from the calls themselves so both real usage and tests can
supply a client without this module ever reaching out to Azure or
requiring credentials just to import it.
"""

import os


def build_client():
    from openai import AzureOpenAI

    return AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
    )


def _complete(client, system_prompt, user_prompt, max_tokens):
    response = client.chat.completions.create(
        model=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def explain_alert(client, ticker, display_name, asset_type, severity, message):
    system_prompt = (
        "You are a markets assistant embedded in a real-time trading "
        "dashboard. Explain the given price/volume anomaly in 1-2 plain "
        "English sentences for a retail investor. Be concrete about what "
        "happened, not generic. Do not give investment advice."
    )
    user_prompt = (
        f"Symbol: {ticker} ({display_name}, {asset_type})\n"
        f"Severity: {severity}\n"
        f"Detected anomaly: {message}"
    )
    return _complete(client, system_prompt, user_prompt, max_tokens=120)


def summarize_day(client, summary_date, alert_summaries):
    system_prompt = (
        "You are a markets assistant embedded in a real-time trading "
        "dashboard. Write a short (3-5 sentence) end-of-day digest of the "
        "anomalies detected today, across all tracked symbols. Be concrete "
        "about which symbols were notable and why. Do not give investment "
        "advice."
    )
    lines = "\n".join(
        f"- {a['ticker']}: {a['severity']} -- {a['message']}"
        for a in alert_summaries
    )
    user_prompt = f"Date: {summary_date}\nAlerts detected today:\n{lines}"
    return _complete(client, system_prompt, user_prompt, max_tokens=250)
