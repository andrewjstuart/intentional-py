# Future Features

Ideas that have been discussed but not built yet, with the steps to build each one. Add new ideas at the end, and move an idea to the [user guide](user-guide.md) once it is implemented.

- [Upload intents directly to Dialogflow](#upload-intents-directly-to-dialogflow)
- [Import zip merged into an agent export](#import-zip-merged-into-an-agent-export)
- [Code-signed Windows executables](#code-signed-windows-executables)

---

## Upload intents directly to Dialogflow

**Status:** tabled. It needs Google Cloud credentials, sign-in and audit logging, which should be designed carefully.

**What it would do:** push the built intents straight into a Dialogflow ES agent, instead of exporting, importing and cleaning up by hand. It could also delete intents that are no longer in the config, after confirmation.

**Considerations**

- Access is through the Dialogflow ES API (`google-cloud-dialogflow`), which needs a Google Cloud project, the agent's project ID, and a signed-in user or service account with the **Dialogflow API Admin** (or Client) role.
- Credentials must never be stored in the repository or in `settings.json`. Prefer Google's own sign-in (`gcloud auth application-default login`) so the tool never handles a key file. If service-account keys are used, keep them outside the project folder.
- Changes made through the API are immediate, so a dry run (the existing `compare` feature) should always be shown and confirmed first.
- Every upload should be logged: who, when, which agent, and which intents were created, updated or deleted.
- Deleting intents is the riskiest part and should be a separate, explicit confirmation.

**Implementation steps**

1. Add an optional `dialogflow` extra in `pyproject.toml` with `google-cloud-dialogflow`, so the CLI and GUI work without it.
2. Add `src/intentional_py/upload.py`:
   - Connect with `dialogflow_v2.IntentsClient()` using Application Default Credentials.
   - List the agent's intents (`list_intents`, with the full intent view) and map them by display name.
   - Convert the built intent JSON into `dialogflow_v2.Intent` objects: training phrases with entity parts, parameters, input contexts, action, priority, and the ML setting.
   - Use `batch_update_intents` to create and update, and `batch_delete_intents` for removals.
3. Reuse `compare` to produce the change list, and require confirmation before anything is sent.
4. Add a CLI command, e.g. `intentional-cli upload --project-id <id> [--delete-missing] [--yes]`, and an **Upload** tab in the GUI that shows the comparison first.
5. Write an upload log file (JSON lines) in the project folder, and show a summary in the results panel.
6. Tests: mock the Dialogflow client and check the requests that would be sent. Never call the real API from the tests or the GitHub workflows.
7. Document the sign-in steps and the required roles in the user guide.

---

## Import zip merged into an agent export

**Status:** tabled. Needs a check of how the Dialogflow console's **Import** and **Restore** behave with a partial zip.

**What it would do:** take the current agent export, add or replace the intents from a build, and produce a new zip that can be imported, so the agent is not left missing the intents that this config does not build.

**Considerations**

- **Restore** replaces the whole agent with the zip, which would delete any intent not in it. That is why a zip of only the new intents is not safe.
- **Import** is documented as adding new intents and replacing ones with the same name, while keeping the rest. Verify this with a test agent first; if it holds, a zip of only the built intents plus the export's `agent.json` and `package.json` may be enough.
- Intents that are no longer used still have to be deleted from the agent by hand. The `compare` results already list them as "only in the export".
- Entities (`entities/`) and agent settings in the export must be kept unchanged.

**Implementation steps**

1. Test **Import** and **Restore** with a copy of an agent to confirm which one keeps unrelated intents.
2. Add `merge_export(export_zip, intents_dir, output_zip)` to `compare.py` or a new module:
   - Copy every file from the export zip except the `intents/` files being replaced.
   - Add the built intent and usersays files, matched by intent name, so the export's copies are replaced.
   - Keep `agent.json`, `package.json` and `entities/` from the export as they are.
3. Add a CLI command, e.g. `intentional-cli package --export agent.zip --output agent_updated.zip`, and a button on the **Compare** tab.
4. Show the comparison with the export, and list the intents that must be deleted by hand, before writing the zip.
5. Tests: build a small export zip, merge a build into it, and check that the unrelated intents and entities are unchanged.

---

## Code-signed Windows executables

**What it would do:** remove the "Windows protected your PC" SmartScreen warning when the executables are first started.

**Considerations**

- Requires a code-signing certificate from a certificate authority (a paid, yearly cost). An EV certificate removes the warning immediately; a standard one builds reputation over time.
- The certificate or signing service credentials must be stored as GitHub Actions secrets, never in the repository.

**Implementation steps**

1. Obtain a certificate, or use a cloud signing service such as Azure Trusted Signing.
2. Add a signing step to `.github/workflows/release.yml` after the PyInstaller builds and before the checksums are written (for example with `signtool` or the signing service's GitHub action).
3. Update the README's Download section to remove the SmartScreen instructions.
