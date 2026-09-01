# Research Grade v2 governance relationship

Research Grade v2 is a parallel contract and policy surface. The frozen v1
`governance/policies/memory-write.policy.json` and its v1 schemas remain
unchanged and continue to govern v1/v1.1 memory behavior. A caller must select
the `2.0.0` profile explicitly; v2 does not silently upgrade or downgrade v1
documents and it does not replace the v1 policy.

The v2 RPM policy adds explicit namespace, programme and project scope,
transactional assessment/approval/commit, event-chain integrity, lifecycle
closure, rights and classification ceilings, and a no-last-writer-wins rule.
The v1 memory policy remains the compatibility baseline while a versioned
migration record and new policy decision are required for any v2 adoption.

The other v2 policies are likewise additive: exchange safety, source-family
diversity, distinct media rights, and Research Grade promotion gates default
to denial or escalation. Policy evaluation is owned by SWOS core; provider,
fixture and specialist-agent outputs cannot self-approve a release.
