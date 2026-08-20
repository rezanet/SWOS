# SWOS Prose live dogfood fixtures

The five `.txt` samples in `live_dogfood/` are intentionally synthetic and public. They contain no private, unpublished, or copyrighted source material and exercise degree/modality, uncertainty, causality/attribution, technical terminology, and numeric/citation preservation.

The trusted SWOS CI live-evidence job runs them through the real rewrite and semantic-verifier providers with `gpt-5.6-luna` and uploads the JSON results as a short-lived Actions artifact. The fixture corpus is empirical evidence, not a formal benchmark and not a release gate by itself.
