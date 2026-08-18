# Production High pipeline

This directory is the canonical runtime implementation copied into
`Dockerfile.high`. A production backend build must be possible from a clean
Good Shepherd checkout; it must never read code from the sibling Formidable
PWA/benchmark repository.

The similarly named modules in `form-idable/benchmarks/wide/` are an
experimental workspace. Changes there do not affect production. Promote an
experiment by applying the reviewed change here, running the unit/container
gates in this repository, then running the frozen all-form and browser gates
documented in `form-idable/docs/design/evals.md`.

Record the Good Shepherd commit, candidate image digest, Formidable evaluator
commit and measured result in Formidable's `chronology/` before production
acceptance.
