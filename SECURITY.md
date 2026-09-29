# Security Policy

## Supported versions

Only the latest release is supported. Please update before reporting an issue.

## Reporting a vulnerability

Please do not open a public issue for security vulnerabilities. Instead, email
andrewjstuart4@gmail.com with a description of the issue and steps to reproduce.
You should get a response within a few days.

## Scope

This tool runs entirely locally: it reads Excel workbooks and config files from
disk and writes Dialogflow ES intent JSON, config, and phrase files. It does not
send data to any network service and does not store credentials. If a future
feature adds direct upload to Dialogflow (see [Future features](docs/future-features.md)),
this policy will be updated to cover credential handling.
