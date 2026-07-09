# Survey Schema Generator

Status: external research tooling.
May authorize code: false.
Runtime owner: none.

This folder contains a reusable Google Apps Script generator and two LyraOS
survey schemas.

It does not add Lyra runtime behavior. It is freeze-safe validation tooling.

## Files

- `google_form_from_schema.gs`
  - Google Apps Script generator.
  - Creates a Google Form from a JSON schema.
  - Creates or opens a Google Sheet.
  - Links Form responses to that Sheet.
  - Writes a `_survey_schema_metadata` sheet with schema/version/form URLs.
- `lyraos_pain_validation_survey.schema.json`
  - Global survey for Telegram, Reddit, Facebook, etc.
  - No Lyra knowledge required.
  - Tests whether plan collapse is painful, recurring, costly, underserved by
    current tools, and strong enough to justify product work now.
- `lyraos_feedback_survey.schema.json`
  - Survey for people who have seen or used Lyra.
  - Tests insight usefulness, intervention accuracy, trust, actionability, and
    perceived user value.

## Quick Use

1. Open <https://script.google.com/>.
2. Create a new Apps Script project.
3. Paste `google_form_from_schema.gs` into `Code.gs`.
4. Open one schema file from this folder.
5. Copy the full JSON object.
6. Replace the `SURVEY_SCHEMA` object at the top of `Code.gs`.
7. Run `buildFormFromActiveSchema()`.
8. Approve Google permissions.
9. Open the logs for:
   - Form edit URL;
   - Form public URL;
   - Responses Sheet URL.

The generated Form is linked to a Sheet automatically.

## Survey Privacy Note

These surveys are external research/validation forms. Responses are stored in
Google Forms/Sheets, not in the LyraOS app database. Do not ask respondents for
raw task titles, provider URLs, tokens, passwords, health details, or other
sensitive personal information.

Each public schema description should disclose:

- participation is voluntary;
- responses are stored by Google Forms/Sheets;
- free-text answers may be reviewed for product research;
- survey answers are self-report and do not prove behavioral change.

## Supported Schema Shape

```json
{
  "id": "stable_schema_id",
  "version": "YYYY-MM-DD",
  "title": "Survey title",
  "description": "Survey description",
  "collectEmail": false,
  "allowResponseEdits": false,
  "showProgressBar": true,
  "confirmationMessage": "Thanks.",
  "destination": {
    "title": "New response sheet title",
    "spreadsheetId": "optional-existing-sheet-id"
  },
  "sections": [
    {
      "id": "section_id",
      "title": "Section title",
      "description": "Optional section intro",
      "questions": [
        {
          "id": "question_id",
          "type": "multiple_choice",
          "title": "Question text",
          "required": true,
          "options": [
            { "label": "Choice A" },
            { "label": "Other", "isOther": true }
          ],
          "metadata": {
            "analysis_bucket": "stable_bucket"
          }
        }
      ]
    }
  ]
}
```

Supported question `type` values:

- `multiple_choice`
- `checkbox`
- `linear_scale`
- `short_answer`
- `paragraph`

## Branching Metadata

Multiple-choice questions may define branches:

```json
{
  "id": "collapse_recency",
  "type": "multiple_choice",
  "options": [{ "label": "This does not happen to me" }],
  "branches": {
    "This does not happen to me": {
      "goToSectionId": "low_pain_exit",
      "reason": "No remembered pain."
    }
  }
}
```

The generator applies Google Forms page navigation for multiple-choice section
jumps. It preserves the full schema in the `_survey_schema_metadata` sheet.
Question `metadata` and `branches` are not shown to respondents by default.
Only set `showMetadataInHelpText: true` on a question for private/debug forms.

Checkbox branching is preserved as metadata only because Google Forms branching
is not reliable for multi-select choices.

Set a section to `"branchOnly": true` when normal respondents should submit
before reaching it and only explicit branches should enter it. This is useful
for low-pain exits.

## Pain Validation Rule

Use `lyraos_pain_validation_survey.schema.json` first for global distribution.

The goal is not to ask whether people like Lyra. The goal is to test:

```text
Do enough people have recurring, costly plan collapse that current tools do not
help them recover from?
```

Provisional product-pain pass:

```text
At least one qualified segment shows:
recurring plan collapse
+ material cost
+ current-tool recovery failure
+ recovery delay or abandoned plan
+ willingness to try a recovery tool during real pressure
```

Segment thresholds are encoded in the schema under
`analysis.segment_validation_thresholds`. The global response pool can be noisy;
do not discard the pain if one coherent segment is strongly positive.

Runtime-fit signals are secondary, not substitutes for pain:

- `overload_entry_behavior`
- `post_collapse_action`
- `metacognitive_warning`
- `missing_visibility`
- `day_one_value`
- `timer_tolerance`

Analysis guardrails:

- `current_tools_fail` is reverse-coded for pain: `1` means current tools mostly
  fail, `5` means they help recovery. Count `1` or `2` as current-tool recovery
  failure.
- `overload_entry_behavior` is a secondary runtime-fit signal, not a primary
  pain-cluster question. Messy-note dumping supports quick-capture fit; "avoid
  looking at the full situation" should be analyzed separately as a visibility
  and control signal by segment.

If no segment shows both the pain cluster and runtime-fit signals, do not force
the product story. Pivot the next cycle toward narrower segment discovery or
pure research.

## Analysis Notes

Do not treat this survey as behavioral truth. It is self-report.

Strong signal:

- concrete recent story;
- material cost;
- repeated pressure-period recurrence;
- current tool failure;
- willingness to tolerate some logging friction during crunch;
- natural entry through messy capture, current-tool recovery failure, and day-1
  value pull for pressure map, recovery inbox, or stale-work resolution.

Weak signal:

- "sounds cool";
- vague productivity interest;
- no recent costly example;
- would only use if fully automatic;
- current tools already solve recovery.

For public distribution, keep the pain survey under five minutes. If completion
rate drops, remove optional open-text fields before removing the pain-cluster
questions.
