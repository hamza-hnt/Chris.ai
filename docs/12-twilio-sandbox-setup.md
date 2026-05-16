# Twilio WhatsApp Sandbox Setup

This guide connects Chris.AI to the Twilio WhatsApp Sandbox.

## Security

Never commit Twilio credentials. Keep the Account SID and Auth Token only in
`.env`.

If an Auth Token was pasted into chat, issue tracker, terminal history, or any
shared surface, rotate it in Twilio after testing.

## Environment

Set these values in `.env`:

```bash
WHATSAPP_MODE=twilio
TWILIO_ACCOUNT_SID=<twilio-account-sid>
TWILIO_AUTH_TOKEN=<twilio-auth-token>
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_VALIDATE_SIGNATURE=false
SLNG_API_KEY=<slng-api-key>
```

`TWILIO_WHATSAPP_FROM` is the default shared Twilio Sandbox WhatsApp sender.
Confirm it in the Twilio Sandbox page and override it if your Sandbox shows a
different sender.

`SLNG_API_KEY` is required for WhatsApp voice notes. Twilio sends inbound media
metadata as `NumMedia`, `MediaUrl0`, and `MediaContentType0`; Chris downloads
audio media from Twilio with the Account SID/Auth Token, transcribes it through
SLNG, and then sends the transcribed text through the same agent pipeline as a
normal WhatsApp message.

The SLNG request uses the Unified STT endpoint:

```text
https://api.slng.ai/v1/bridges/unmute/stt/slng/deepgram/nova:3-multi
```

WhatsApp voice notes usually arrive from Twilio as `audio/ogg`; Chris sends
those to SLNG with `encoding=opus`.

For production-like testing, set:

```bash
TWILIO_VALIDATE_SIGNATURE=true
```

Keep it `false` while debugging ngrok URL changes, because Twilio signatures are
sensitive to the exact public callback URL.

Restart the backend after editing `.env`:

```bash
docker compose up -d --force-recreate backend
```

## Local Tunnel

Twilio needs a public HTTPS endpoint:

```bash
ngrok http 8000
```

Use the HTTPS forwarding URL with this path:

```text
https://<ngrok-subdomain>.ngrok-free.app/webhooks/twilio/whatsapp
```

## Twilio Console

In Twilio Console:

1. Open Messaging > Try it out > Send a WhatsApp message.
2. Join the Sandbox from your personal WhatsApp by sending the displayed
   `join ...` phrase to the Sandbox number.
3. In Sandbox settings, set **When a message comes in** to:

   ```text
   https://<ngrok-subdomain>.ngrok-free.app/webhooks/twilio/whatsapp
   ```

4. Method: `POST`.
5. Save.

## Seeded Contact Mapping

Chris routes incoming WhatsApp messages by matching the sender phone number to
`users.phone`.

After `make seed`, replace a demo tenant phone with your real WhatsApp number in
E.164 format:

```bash
set -a; source .env; set +a

docker compose exec postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "update users set phone = '+33612345678' where email = 'amina.tenant@example.com';"
```

Use the same number that joined the Twilio Sandbox.

## Smoke Test

Local webhook test without Twilio:

```bash
curl -X POST http://localhost:8000/webhooks/twilio/whatsapp \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "From=whatsapp:+33600000001" \
  --data-urlencode "Body=There is a leak under the sink" \
  --data-urlencode "MessageSid=SMlocaltwiliotest"
```

Expected response:

```json
{
  "status": "received",
  "provider": "twilio"
}
```

Then test end to end from WhatsApp:

1. Send a message from the joined WhatsApp number to the Twilio Sandbox number.
2. Send a short WhatsApp voice note from the same number. In backend logs, the
   webhook should log `Twilio voice message transcribed` and then normal agent
   activity.
3. Watch backend logs:

   ```bash
   docker compose logs -f backend
   ```

4. Open the dashboard at `http://localhost:5173` and log in as
   `amina.tenant@example.com` or `hamza.landlord@example.com`.

## Current Limits

- Text inbound messages are supported.
- Audio inbound messages are supported when Twilio provides an `audio/*`
  `MediaContentType` and SLNG can transcribe the file.
- Non-audio media inbound messages are acknowledged as empty or unsupported for
  now.
- Outbound messages use Twilio Programmable Messaging REST API.
- Sandbox outbound only works for WhatsApp numbers that joined the Sandbox.
- The current agent sends operational replies synchronously during the webhook
  request; move this behind a queue before production load.
