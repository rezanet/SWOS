# Retention and Deletion

| Artefact | Default retention | Trigger for review |
|---|---|---|
| Evidence matrix | Life of the output plus 7 years | Output retirement |
| Provenance bundle | Life of the output plus 7 years | Output retirement |
| Decision ledger | Permanent (append-only) | Never deleted; entries retire |
| RPM items | Per-category expiry, default 24 months | Expiry date, correction, contradiction |
| Episodic memory | Life of the work item | Work closure |
| User memory | Until user deletion | User request |
| Evaluation results | 5 releases or 3 years | Superseded baseline |
| Security events | 7 years | Regulatory |
| Retrieved source content | **Not retained** above excerpt limits | Continuous |

## Deletion is a rights operation

Deletion is triggered by a data subject request, a licence revocation, a
classification error, or retention expiry. It is **not** a tidiness operation and
is never used to remove inconvenient history.

Deletion writes **deletion evidence**: what was deleted, why, under what
authority, when, and by whom. The item's existence and its removal remain
provable. Its content does not.

## Expiry versus deletion

Expiry is a **visibility** change: an expired memory item stops being returned to
agents but remains in the audit trail. Deletion is a **rights** operation:
content is removed and evidence of removal is retained. Conflating them produces
either silent data retention or unauditable data loss.

## Retirement

Retiring an output requires a retirement checklist, archival of the provenance
bundle, an SDL `retirement` entry, and de-registration from any inventory.
Deleting history is not retirement.
