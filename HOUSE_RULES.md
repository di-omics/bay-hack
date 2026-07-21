# Repository house rules

## Authorship

- Git author and committer name must be `di-omics`.
- Commits describe the product change, not the coding tool used to make it.
- Do not add assistant attribution, generated-by notes, or co-author trailers.
- Preserve the existing GitHub profile, avatar, and public identity.

## Writing style

- Do not use em dashes.
- Prefer short sentences, colons, parentheses, commas, or a new sentence.
- Use `di-omics` when naming the author or project owner.
- Keep claims bounded by evidence. Label every value as modeled, simulated,
  measured, or hardware-validated.

## Engineering

- Keep `python -m bayhack.demo` dependency-free and green.
- Verify every physical plan before execution.
- Gate seed experiments exactly like optimization experiments.
- Never train the world model on an untrusted measurement.
- Never hide seed runs, retries, or failed gates from the trust ledger.
- Keep hardware behind adapters. The simulator is always the fallback.
- Use a unique tip for every liquid transfer.
- Run tests, the demo, and the benchmark before every push.

## Git

- Use factual Conventional Commit subjects.
- Keep commits small enough to review and revert.
- Do not rewrite public history unless `di-omics` explicitly requests it.
- Do not modify the GitHub profile repository or avatar from this project.

