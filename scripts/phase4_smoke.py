import requests, json, sys

BASE = 'http://localhost:5000/api/v2.5'
WS = 'ws_SEED0100000000000000000000'
DOC = 'doc_SEED0100000000000000000000'

ANALYST = {'Authorization': 'Bearer usr_SEED0100000000000000000000'}
VERIFIER = {'Authorization': 'Bearer usr_SEED0200000000000000000000'}
ADMIN = {'Authorization': 'Bearer usr_SEED0300000000000000000000'}

def d(r): return r.json().get('data', r.json())

results = []

# === RFI ROLE ENFORCEMENT ===
r = requests.post(f'{BASE}/workspaces/{WS}/rfis', json={'target_record_id':'rec_p4_final','question':'Q1'}, headers=ANALYST)
rfi = d(r); rfi_id, rfi_v = rfi.get('id'), rfi.get('version',1)
results.append(('1. RFI create (analyst)', r.status_code == 201, r.status_code))

r = requests.patch(f'{BASE}/rfis/{rfi_id}', json={'custody_status':'awaiting_verifier','version':rfi_v}, headers=ANALYST)
rfi_v = d(r).get('version', rfi_v+1) if r.status_code==200 else rfi_v
results.append(('2. RFI send (analyst OK)', r.status_code == 200, r.status_code))

r2c = requests.post(f'{BASE}/workspaces/{WS}/rfis', json={'target_record_id':'rec_p4_final2','question':'Q2'}, headers=ANALYST)
rfi2 = d(r2c); rfi_id2, rfi_v2 = rfi2.get('id'), rfi2.get('version',1)
r = requests.patch(f'{BASE}/rfis/{rfi_id2}', json={'custody_status':'awaiting_verifier','version':rfi_v2}, headers=VERIFIER)
results.append(('3. RFI send (verifier blocked 403)', r.status_code == 403, r.status_code))
results.append(('3b. ROLE_NOT_ALLOWED code', 'ROLE_NOT_ALLOWED' in r.text, ''))

r = requests.patch(f'{BASE}/rfis/{rfi_id}', json={'custody_status':'resolved','version':rfi_v}, headers=VERIFIER)
results.append(('4. RFI resolve (verifier OK)', r.status_code == 200, r.status_code))

r_s = requests.patch(f'{BASE}/rfis/{rfi_id2}', json={'custody_status':'awaiting_verifier','version':rfi_v2}, headers=ANALYST)
rfi_v2 = d(r_s).get('version', rfi_v2+1) if r_s.status_code==200 else rfi_v2
r = requests.patch(f'{BASE}/rfis/{rfi_id2}', json={'custody_status':'resolved','version':rfi_v2}, headers=ANALYST)
results.append(('5. RFI resolve (analyst blocked 403)', r.status_code == 403, r.status_code))

# === CORRECTION ROLE ENFORCEMENT ===
r_a1 = requests.post(f'{BASE}/documents/{DOC}/anchors', json={'node_id':'n_p4f1','field_key':'f_p4_1','selected_text':'text','char_start':0,'char_end':4,'page_number':1}, headers=ANALYST)
aid1 = d(r_a1).get('id')
r_a2 = requests.post(f'{BASE}/documents/{DOC}/anchors', json={'node_id':'n_p4f2','field_key':'f_p4_2','selected_text':'text2','char_start':5,'char_end':10,'page_number':1}, headers=ANALYST)
aid2 = d(r_a2).get('id')

r = requests.post(f'{BASE}/documents/{DOC}/corrections', json={'anchor_id':aid1,'field_key':'f_p4_1','original_value':'Short','corrected_value':'A Much Longer Corrected Value Here'}, headers=ANALYST)
corr = d(r); cid, cv = corr.get('id'), corr.get('version',1)
results.append(('6. Correction create (non-trivial)', r.status_code == 201, r.status_code))
results.append(('6b. Status pending_verifier', corr.get('status') == 'pending_verifier', corr.get('status')))

r = requests.patch(f'{BASE}/corrections/{cid}', json={'status':'approved','version':cv}, headers=VERIFIER)
results.append(('7. Correction approve (verifier OK)', r.status_code == 200, r.status_code))

r = requests.post(f'{BASE}/documents/{DOC}/corrections', json={'anchor_id':aid2,'field_key':'f_p4_2','original_value':'Brief','corrected_value':'A Different Much Longer Value'}, headers=ANALYST)
corr2 = d(r); cid2, cv2 = corr2.get('id'), corr2.get('version',1)
r = requests.patch(f'{BASE}/corrections/{cid2}', json={'status':'approved','version':cv2}, headers=ANALYST)
results.append(('8. Correction approve (analyst blocked 403)', r.status_code == 403, r.status_code))
results.append(('8b. ROLE_NOT_ALLOWED code', 'ROLE_NOT_ALLOWED' in r.text, ''))

# === OCR ESCALATION + IDEMPOTENCY ===
r = requests.post(f'{BASE}/documents/{DOC}/ocr-escalations', json={'escalation_type':'ocr_reprocess','quality_flag':'suspect_mojibake'}, headers=ANALYST)
first = r.status_code
r2 = requests.post(f'{BASE}/documents/{DOC}/ocr-escalations', json={'escalation_type':'ocr_reprocess','quality_flag':'suspect_mojibake'}, headers=ANALYST)
results.append(('9. OCR escalation create', first in (200, 201), first))
results.append(('10. OCR escalation idempotent (200)', r2.status_code == 200, r2.status_code))
results.append(('10b. _idempotent flag', d(r2).get('_idempotent') == True, d(r2).get('_idempotent')))

# === AUDIT EVENTS ===
r = requests.get(f'{BASE}/workspaces/{WS}/audit-events?limit=200', headers=ADMIN)
events = d(r) if isinstance(d(r), list) else d(r).get('items', [])
etypes = [e.get('event_type') for e in events if isinstance(e, dict)]
results.append(('11. Audit: MOJIBAKE_ESCALATION_REQUESTED', 'MOJIBAKE_ESCALATION_REQUESTED' in etypes, 'found'))
results.append(('12. Audit: RFI_CREATED', 'RFI_CREATED' in etypes, 'found'))

# === SUMMARY ===
print('=' * 65)
print('PHASE 4 COMPREHENSIVE SMOKE TEST - FINAL')
print('=' * 65)
p = sum(1 for _, ok, _ in results if ok)
f = sum(1 for _, ok, _ in results if not ok)
for name, ok, detail in results:
    sym = 'PASS' if ok else 'FAIL'
    print(f'  [{sym}] {name}: {detail}')
print(f'\nTOTAL: {p}/{len(results)} passed, {f} failed')
if f == 0:
    print('\n  >>> ALL PHASE 4 TESTS PASS <<<')
    sys.exit(0)
else:
    sys.exit(1)
