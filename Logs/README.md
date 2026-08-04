# Logs

This folder contains execution logs created by the Japanese Corpus Pipeline.

## Purpose

Logs record what each script did while processing data.

They are intended for:

- Auditing
- Troubleshooting
- Performance monitoring
- Recovery after failures

Logs are **not** part of the corpus database.

---

## Folder Structure

```
Logs/
│
├── Analysis/
├── Cleaning/
├── Corpus Builder/
├── DeepSeek Client/
├── Job Builder/
├── Job Creation/
├── Merging/
├── Processing/
├── Production Manager/
├── Request Builder/
├── Source Intake/
├── Subtitle Cleaner/
└── Transcript Cleaner/
```

Each subfolder contains logs produced by one stage/script.

---

## Log Philosophy

Data and logs are intentionally separated.

### Data folders

Contain corpus data that moves through the pipeline.

Examples:

- Raw Transcripts
- Cleaned Archive
- Transcript Processor/jsonl

### Log folders

Contain records describing what the programs did.

Examples:

- files processed
- timestamps
- API usage
- validation results
- errors
- execution summaries

---

## Design Principles

The pipeline is built around small, single-purpose scripts.

Each script should:

- perform one job well
- write a log
- never overwrite previous logs
- fail safely
- be restartable whenever practical

---

## Temporary Files

Temporary working files (jobs, responses, completed jobs) are **not** logs.

They exist only to allow interrupted processing to resume without repeating successful API calls.

They may be deleted automatically after a successful run.

Logs are permanent.

---

Japanese Corpus Pipeline