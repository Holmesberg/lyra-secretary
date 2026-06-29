/**
 * Google Forms survey generator from a JSON schema.
 *
 * Usage:
 * 1. Open https://script.google.com/ and create a new Apps Script project.
 * 2. Paste this file into Code.gs.
 * 3. Paste one schema object into SURVEY_SCHEMA below.
 * 4. Run buildFormFromActiveSchema().
 *
 * Responses are linked to a newly-created Google Sheet unless
 * schema.destination.spreadsheetId is provided.
 */

var SURVEY_SCHEMA = {
  title: "Replace this with a survey schema",
  description: "Paste a schema from docs/surveys/*.json into SURVEY_SCHEMA.",
  sections: []
};

function buildFormFromActiveSchema() {
  return buildFormFromSchema(SURVEY_SCHEMA);
}

function buildFormFromJsonString(jsonText) {
  return buildFormFromSchema(JSON.parse(jsonText));
}

function buildFormFromSchema(schema) {
  validateSchema_(schema);

  var form = FormApp.create(schema.title);
  form.setDescription(schema.description || "");
  form.setCollectEmail(Boolean(schema.collectEmail));
  form.setAllowResponseEdits(Boolean(schema.allowResponseEdits));
  form.setProgressBar(Boolean(schema.showProgressBar));
  form.setConfirmationMessage(
    schema.confirmationMessage ||
      "Thank you. Your response was recorded."
  );

  var spreadsheet = linkResponseSheet_(form, schema);
  var context = {
    form: form,
    sectionById: {},
    questionItems: [],
    pendingBranches: []
  };

  addSectionsAndQuestions_(schema, context);
  applyBranches_(context);
  writeMetadataSheet_(spreadsheet, schema, form);

  Logger.log("Form edit URL: " + form.getEditUrl());
  Logger.log("Form public URL: " + form.getPublishedUrl());
  Logger.log("Responses sheet URL: " + spreadsheet.getUrl());

  return {
    formId: form.getId(),
    editUrl: form.getEditUrl(),
    publishedUrl: form.getPublishedUrl(),
    spreadsheetId: spreadsheet.getId(),
    spreadsheetUrl: spreadsheet.getUrl()
  };
}

function validateSchema_(schema) {
  if (!schema || typeof schema !== "object") {
    throw new Error("Schema must be an object.");
  }
  if (!schema.title) {
    throw new Error("Schema title is required.");
  }
  if (!Array.isArray(schema.sections) || schema.sections.length === 0) {
    throw new Error("Schema sections must be a non-empty array.");
  }
}

function linkResponseSheet_(form, schema) {
  var destination = schema.destination || {};
  var spreadsheet;
  if (destination.spreadsheetId) {
    spreadsheet = SpreadsheetApp.openById(destination.spreadsheetId);
  } else {
    spreadsheet = SpreadsheetApp.create(
      destination.title || schema.title + " - Responses"
    );
  }
  form.setDestination(FormApp.DestinationType.SPREADSHEET, spreadsheet.getId());
  return spreadsheet;
}

function addSectionsAndQuestions_(schema, context) {
  schema.sections.forEach(function (section, index) {
    validateSection_(section);
    var pageBreak = null;
    if (index > 0) {
      pageBreak = context.form.addPageBreakItem();
      pageBreak.setTitle(section.title);
      if (section.description) {
        pageBreak.setHelpText(section.description);
      }
      if (section.branchOnly === true) {
        pageBreak.setGoToPage(FormApp.PageNavigationType.SUBMIT);
      }
      context.sectionById[section.id] = pageBreak;
    } else {
      context.sectionById[section.id] = null;
      if (section.description) {
        context.form.setDescription(
          [schema.description || "", section.description].filter(Boolean).join("\n\n")
        );
      }
    }

    (section.questions || []).forEach(function (question) {
      var item = addQuestion_(context.form, question);
      context.questionItems.push({ question: question, item: item });
      if (question.branches) {
        context.pendingBranches.push({ question: question, item: item });
      }
    });
  });
}

function validateSection_(section) {
  if (!section.id) throw new Error("Every section needs an id.");
  if (!section.title) throw new Error("Section " + section.id + " needs a title.");
}

function addQuestion_(form, question) {
  if (!question.id) throw new Error("Every question needs an id.");
  if (!question.title) throw new Error("Question " + question.id + " needs a title.");

  var type = String(question.type || "").toLowerCase();
  var item;

  if (type === "multiple_choice") {
    item = form.addMultipleChoiceItem();
    item.setTitle(question.title);
    item.setRequired(Boolean(question.required));
    var multipleChoiceOptions = (question.options || []).filter(function (option) {
      return !(option && option.isOther === true);
    });
    item.setChoices(multipleChoiceOptions.map(function (option) {
      return item.createChoice(option.label || String(option));
    }));
    if (hasOtherOption_(question)) {
      item.showOtherOption(true);
    }
  } else if (type === "checkbox") {
    item = form.addCheckboxItem();
    item.setTitle(question.title);
    item.setRequired(Boolean(question.required));
    var checkboxOptions = (question.options || []).filter(function (option) {
      return !(option && option.isOther === true);
    });
    item.setChoices(checkboxOptions.map(function (option) {
      return item.createChoice(option.label || String(option));
    }));
    if (hasOtherOption_(question)) {
      item.showOtherOption(true);
    }
  } else if (type === "linear_scale") {
    item = form.addScaleItem();
    item.setTitle(question.title);
    item.setRequired(Boolean(question.required));
    item.setBounds(question.lowerBound || 1, question.upperBound || 5);
    if (question.lowerLabel || question.upperLabel) {
      item.setLabels(question.lowerLabel || "", question.upperLabel || "");
    }
  } else if (type === "short_answer") {
    item = form.addTextItem();
    item.setTitle(question.title);
    item.setRequired(Boolean(question.required));
  } else if (type === "paragraph") {
    item = form.addParagraphTextItem();
    item.setTitle(question.title);
    item.setRequired(Boolean(question.required));
  } else {
    throw new Error("Unsupported question type for " + question.id + ": " + type);
  }

  var helpText = buildHelpText_(question);
  if (helpText) {
    item.setHelpText(helpText);
  }
  return item;
}

function hasOtherOption_(question) {
  return (question.options || []).some(function (option) {
    return option && option.isOther === true;
  });
}

function buildHelpText_(question) {
  var parts = [];
  if (question.description) parts.push(question.description);
  if (question.metadata && question.showMetadataInHelpText === true) {
    parts.push("Metadata: " + JSON.stringify(question.metadata));
  }
  if (question.branches && question.showMetadataInHelpText === true) {
    parts.push("Branching metadata: " + JSON.stringify(question.branches));
  }
  return parts.join("\n");
}

function applyBranches_(context) {
  context.pendingBranches.forEach(function (entry) {
    var question = entry.question;
    var item = entry.item;
    var type = String(question.type || "").toLowerCase();

    if (type !== "multiple_choice") {
      return;
    }

    var branches = question.branches || {};
    var options = question.options || [];
    var choices = options.map(function (option) {
      var label = option.label || String(option);
      var branch = branches[label] || branches[option.value];
      if (branch && branch.goToSectionId) {
        var target = context.sectionById[branch.goToSectionId];
        if (!target) {
          throw new Error(
            "Question " +
              question.id +
              " points to missing/non-branchable section: " +
              branch.goToSectionId
          );
        }
        return item.createChoice(label, target);
      }
      if (branch && branch.submit === true) {
        return item.createChoice(label, FormApp.PageNavigationType.SUBMIT);
      }
      return item.createChoice(label, FormApp.PageNavigationType.CONTINUE);
    });
    item.setChoices(choices);
  });
}

function writeMetadataSheet_(spreadsheet, schema, form) {
  var sheetName = "_survey_schema_metadata";
  var sheet = spreadsheet.getSheetByName(sheetName);
  if (!sheet) {
    sheet = spreadsheet.insertSheet(sheetName);
  }
  sheet.clear();
  sheet.getRange(1, 1, 1, 2).setValues([["key", "value"]]);
  sheet.getRange(2, 1, 6, 2).setValues([
    ["schema_id", schema.id || ""],
    ["schema_version", schema.version || ""],
    ["form_id", form.getId()],
    ["form_edit_url", form.getEditUrl()],
    ["form_public_url", form.getPublishedUrl()],
    ["generated_at", new Date().toISOString()]
  ]);
  sheet.getRange(9, 1).setValue("schema_json");
  sheet.getRange(9, 2).setValue(JSON.stringify(schema, null, 2));
}
