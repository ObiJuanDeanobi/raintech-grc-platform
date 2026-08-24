# Local Evidence Operating Boundary

## Operators

Only safe scope metadata and evidence that has already been approved and
sanitized may enter this local application. Keep actual CUI, PHI, and ePHI
upstream. That exclusion includes source content, samples, screenshots, and
exports containing those data types.

Use the direct file picker only for synthetic material or approved sanitized
evidence. The application stores the selected file under its managed local file
root and captures its initial immutable version and SHA-256 value.

V1 has no in-application content scanner and no upload attestation prompt.
Those omissions are an accepted V1 residual risk: the upstream engagement
practice is the control. Johnathan must reconsider this boundary if the
engagement process, user population, or deployment model changes.

## Developers

Tests, fixtures, demonstrations, screenshots, and committed sample material
must be synthetic or have recorded sanitization approval. Do not commit or add
actual CUI, PHI, ePHI, client source content, samples, screenshots, or exports.

Do not claim that the application scans, classifies, warns on, or attests to
evidence content. None of those backstops exists in V1. Preserve the project
ownership checks on evidence routes and calculate the captured SHA-256 from the
bytes read back from application-managed local storage.
