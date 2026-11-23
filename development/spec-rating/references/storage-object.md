# Storage: object storage (S3/GCS/OSS class blobs)

## What a complete object-storage spec documents
- Bucket/container layout: prefix scheme (what partitions where), naming grammar.
- Lifecycle: per class — transition to cold storage, expiry, legal-hold exceptions.
- Access control: who/what reads/writes which prefix; presigned URL policy and lifetime.
- Consistency semantics: read-after-write guarantees, listing consistency, multipart abort.
- Versioning: on or off per bucket class; what restores look like; ransomware story.

## The questions the spec must answer
- What is the size distribution and the traffic shape (many small reads? few huge?),
  because it decides multipart thresholds and egress costs.
- What happens on upload failure mid-multipart (orphan parts, who cleans, when)?
- Immutability/compliance: which objects are write-once, and what enforces it?
- Cost model at stated volume: storage + requests + egress, so nobody is surprised.

## Rating checks
- FAIL if any prefix has no lifecycle policy (orphan accumulation is the default outcome).
- FAIL if presigned-URL lifetime is unstated.
- FAIL if delete is assumed instant/complete with no versioning or grace period.
