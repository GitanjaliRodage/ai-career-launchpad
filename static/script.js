/* AI Career Launchpad - front-end logic.
   Talks only to the /api/analyze endpoint. No secrets are ever handled here. */

(function () {
  "use strict";

  var form = document.getElementById("analyze-form");
  var dropzone = document.getElementById("dropzone");
  var fileInput = document.getElementById("resume");
  var fileHint = document.getElementById("file-hint");
  var resumeError = document.getElementById("resume-error");
  var jdInput = document.getElementById("job_description");
  var jdError = document.getElementById("jd-error");
  var charCount = document.getElementById("char-count");
  var alertBox = document.getElementById("form-alert");
  var submitBtn = document.getElementById("submit-btn");
  var loading = document.getElementById("loading");
  var loadingStep = document.getElementById("loading-step");
  var results = document.getElementById("results");

  var selectedFile = null;
  var MAX_BYTES = 5 * 1024 * 1024;
  var MIN_JD_CHARS = 60;

  var LOADING_STEPS = [
    "Reading your resume",
    "Extracting skills and experience",
    "Comparing against the job requirements",
    "Building your personalised action plan"
  ];

  /* ---------------- file selection ---------------- */
  dropzone.addEventListener("click", function () { fileInput.click(); });
  dropzone.addEventListener("keydown", function (e) {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInput.click(); }
  });

  fileInput.addEventListener("change", function () {
    selectFile(fileInput.files[0]);
  });

  ["dragenter", "dragover"].forEach(function (evt) {
    dropzone.addEventListener(evt, function (e) {
      e.preventDefault(); dropzone.classList.add("dragover");
    });
  });
  ["dragleave", "drop"].forEach(function (evt) {
    dropzone.addEventListener(evt, function (e) {
      e.preventDefault(); dropzone.classList.remove("dragover");
    });
  });
  dropzone.addEventListener("drop", function (e) {
    if (e.dataTransfer && e.dataTransfer.files.length) selectFile(e.dataTransfer.files[0]);
  });

  function selectFile(file) {
    resumeError.hidden = true;
    dropzone.classList.remove("invalid");

    if (!file) { resetFile(); return; }

    var name = file.name || "";
    var isPdf = name.toLowerCase().slice(-4) === ".pdf" || file.type === "application/pdf";

    if (!isPdf) {
      setFileError("Only PDF resumes are supported.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setFileError("That file is larger than 5 MB. Please upload a smaller PDF.");
      return;
    }

    selectedFile = file;
    dropzone.classList.add("has-file");
    fileHint.textContent = name + "  (" + Math.round(file.size / 1024) + " KB)";
    fileHint.classList.add("ok");
  }

  function setFileError(message) {
    selectedFile = null;
    fileInput.value = "";
    dropzone.classList.add("invalid");
    dropzone.classList.remove("has-file");
    fileHint.textContent = "PDF only, up to 5 MB. Text-based PDFs work best.";
    fileHint.classList.remove("ok");
    resumeError.textContent = message;
    resumeError.hidden = false;
  }

  function resetFile() {
    selectedFile = null;
    fileInput.value = "";
    dropzone.classList.remove("has-file", "invalid");
    fileHint.textContent = "PDF only, up to 5 MB. Text-based PDFs work best.";
    fileHint.classList.remove("ok");
    resumeError.hidden = true;
  }

  /* ---------------- job description counter ---------------- */
  jdInput.addEventListener("input", function () {
    var len = jdInput.value.trim().length;
    charCount.textContent = len + (len === 1 ? " character" : " characters");
    if (len >= MIN_JD_CHARS) {
      jdError.hidden = true;
      jdInput.classList.remove("invalid");
    }
  });

  /* ---------------- submit ---------------- */
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    alertBox.hidden = true;
    resumeError.hidden = true;
    jdError.hidden = true;

    var valid = true;

    if (!selectedFile) {
      setFileError("Please choose your resume PDF first.");
      valid = false;
    }

    var jd = jdInput.value.trim();
    if (jd.length < MIN_JD_CHARS) {
      jdError.textContent = "Paste the full job description (at least " + MIN_JD_CHARS + " characters).";
      jdError.hidden = false;
      jdInput.classList.add("invalid");
      valid = false;
    }

    if (!valid) return;

    var payload = new FormData();
    payload.append("resume", selectedFile);
    payload.append("job_description", jd);

    setLoading(true);
    animateSteps();

    fetch("/api/analyze", { method: "POST", body: payload })
      .then(function (response) {
        return response.json()
          .catch(function () { throw new Error("The server returned an unexpected response."); })
          .then(function (data) {
            if (!response.ok || !data.success) {
              throw new Error(data.error || "Analysis failed. Please try again.");
            }
            return data.analysis;
          });
      })
      .then(function (analysis) {
        renderResults(analysis);
        results.scrollIntoView({ behavior: "smooth", block: "start" });
      })
      .catch(function (err) {
        showError(err.message || "Something went wrong. Please try again.");
      })
      .finally(function () {
        setLoading(false);
      });
  });

  var stepTimer = null;
  function animateSteps() {
    var index = 0;
    loadingStep.textContent = LOADING_STEPS[0];
    clearInterval(stepTimer);
    stepTimer = setInterval(function () {
      index = (index + 1) % LOADING_STEPS.length;
      loadingStep.textContent = LOADING_STEPS[index];
    }, 1600);
  }

  function setLoading(state) {
    loading.hidden = !state;
    submitBtn.disabled = state;
    submitBtn.textContent = state ? "Analysing..." : "Analyse My Career Fit";
    if (state) clearInterval(stepTimer);
  }

  function showError(message) {
    alertBox.textContent = message;
    alertBox.hidden = false;
    alertBox.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  /* ---------------- rendering ---------------- */
  function renderResults(a) {
    var score = typeof a.fit_score === "number" ? a.fit_score : 0;
    var matched = a.matched_skills || [];
    var gaps = a.skill_gaps || [];

    document.getElementById("fit-score").textContent = score;
    document.getElementById("score-ring").style.setProperty("--pct", score);
    document.getElementById("score-ring").style.setProperty(
      "--ring", score >= 75 ? "#34d399" : score >= 50 ? "#7c5cff" : "#fbbf24"
    );
    document.getElementById("score-headline").textContent = headlineFor(score);
    document.getElementById("score-description").textContent = a.summary || defaultDescription(score);
    document.getElementById("matched-count").textContent = matched.length;
    document.getElementById("gap-count").textContent = gaps.length;
    document.getElementById("provider-name").textContent =
      a.provider === "mock" ? "Mock (local development)" : "Amazon Bedrock (" + (a.provider || "bedrock") + ")";

    document.getElementById("result-summary").textContent =
      "How your current experience lines up with this specific role.";

    renderChips("matched-skills", matched, "ok", "No matching skills detected yet.");
    renderChips("skill-gaps", gaps, "gap", "No skill gaps identified. Strong fit.");
    renderList("strengths", a.strengths, "No strengths were returned for this analysis.");
    renderList("improvements", a.improvement_areas, "No improvement areas were returned.");
    renderList("action-plan", a.action_plan, "No action plan was returned.");
    renderList("next-steps", a.next_steps, "No next steps were returned.");

    results.hidden = false;
  }

  function headlineFor(score) {
    if (score >= 80) return "Excellent fit - keep building in this direction.";
    if (score >= 60) return "Good fit - a focused plan should make you competitive.";
    if (score >= 40) return "Partial fit - targeted upskilling can move you into range.";
    return "Early-stage fit - start with the foundations in your plan.";
  }

  function defaultDescription(score) {
    return "Your career fit score is " + score + " out of 100. Review the breakdown below to see what to emphasise and what to work on next.";
  }

  function renderChips(id, items, cls, emptyText) {
    var box = document.getElementById(id);
    box.innerHTML = "";
    if (!items || items.length === 0) {
      var empty = document.createElement("span");
      empty.className = "chip empty";
      empty.textContent = emptyText;
      box.appendChild(empty);
      return;
    }
    items.forEach(function (item) {
      var chip = document.createElement("span");
      chip.className = "chip " + cls;
      chip.textContent = item;
      box.appendChild(chip);
    });
  }

  function renderList(id, items, emptyText) {
    var box = document.getElementById(id);
    box.innerHTML = "";
    if (!items || items.length === 0) {
      var li = document.createElement("li");
      li.textContent = emptyText;
      box.appendChild(li);
      return;
    }
    items.forEach(function (item) {
      var li = document.createElement("li");
      li.textContent = item;
      box.appendChild(li);
    });
  }

  /* ---------------- analyse again ---------------- */
  document.getElementById("analyse-again").addEventListener("click", function () {
    results.hidden = true;
    resetFile();
    jdInput.value = "";
    charCount.textContent = "0 characters";
    alertBox.hidden = true;
    document.getElementById("analyze").scrollIntoView({ behavior: "smooth", block: "start" });
  });
})();