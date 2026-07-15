# TapSafe Starter

A local Flask prototype for comparing an insecure permanent NFC link with layered, revocable access.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/init_db.py
python run.py
```

Open:
- `http://127.0.0.1:5000/`
- Baseline: `/baseline/demo-card`
- Defended: `/tap/demo-token-001`
- Admin: `/admin/cards`
- Audit: `/admin/audit`

Demo PIN: `2468`

## Evaluate

```bash
pytest -q
python scripts/run_evaluation.py
```

The evaluation JSON is saved under `evidence/test-results/`.

## NFC card

Encode the defended URL on the physical card. For a phone demo, use the laptop's private LAN IP while both devices are on the same private network. Do not expose the intentionally weak baseline publicly.

## Safety

Synthetic data only. Local testing only. Not a medical device and not a substitute for professional or emergency support.

## Physical NFC tap route

TapSafe now includes a dedicated NFC entry endpoint:

```text
http://<MAC-LAN-IP>:5050/nfc/demo-token-001
```

Open `http://<MAC-LAN-IP>:5050/admin/nfc-setup` to copy the exact URL shown by the running application. Write that URL to the card with NFC Tools. A physical-card entry creates an `nfc_tap` audit event and then redirects to the defended public disclosure layer. Possession of the card does not unlock protected information.
