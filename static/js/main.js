function setupCharCounters() {
    document.querySelectorAll(".char-counter").forEach(function (counter) {
        var input = document.getElementById(counter.dataset.for);
        if (!input) return;
        var max = parseInt(counter.dataset.max, 10);
        function update() {
            counter.textContent = input.value.length + "/" + max;
        }
        input.addEventListener("input", update);
        update();
    });
}

function setupDynamicOptionFields() {
    var addButton = document.getElementById("add-option");
    if (!addButton) return;

    var optionFields = document.querySelectorAll(".option-field");

    addButton.addEventListener("click", function () {
        for (var i = 0; i < optionFields.length; i++) {
            if (optionFields[i].hasAttribute("hidden")) {
                optionFields[i].removeAttribute("hidden");
                break;
            }
        }
        var anyHidden = Array.prototype.some.call(optionFields, function (field) {
            return field.hasAttribute("hidden");
        });
        if (!anyHidden) {
            addButton.setAttribute("hidden", "");
        }
    });

    optionFields.forEach(function (field) {
        var removeButton = field.querySelector(".option-remove");
        if (!removeButton) return;
        removeButton.addEventListener("click", function () {
            field.querySelector("input").value = "";
            field.setAttribute("hidden", "");
            addButton.removeAttribute("hidden");
        });
    });
}

function getCookie(name) {
    var prefix = name + "=";
    var parts = document.cookie.split("; ");
    for (var i = 0; i < parts.length; i++) {
        if (parts[i].indexOf(prefix) === 0) {
            return decodeURIComponent(parts[i].slice(prefix.length));
        }
    }
    return null;
}

function renderPollResults(container, data) {
    var optionsWrapper = container.querySelector(".poll-options");
    var ul = document.createElement("ul");
    ul.className = "poll-results";

    data.results.forEach(function (result, index) {
        var isSelected = result.option_id === data.voted_option_id;
        var li = document.createElement("li");
        li.className = "poll-result" + (isSelected ? " selected" : "");
        li.dataset.optionId = result.option_id;
        li.dataset.order = index;
        li.setAttribute("role", "progressbar");
        li.setAttribute("aria-valuenow", result.percent);
        li.setAttribute("aria-valuemin", "0");
        li.setAttribute("aria-valuemax", "100");
        li.setAttribute(
            "aria-label",
            result.text + ": yüzde " + result.percent + ", " + result.votes + " oy" + (isSelected ? ", senin seçimin" : "")
        );

        var bar = document.createElement("span");
        bar.className = "poll-result-bar";
        bar.style.width = "0%";
        bar.setAttribute("aria-hidden", "true");

        var label = document.createElement("span");
        label.className = "poll-result-label";
        label.setAttribute("aria-hidden", "true");
        label.textContent = result.text + " — %" + result.percent + " (" + result.votes + ")" + (isSelected ? " ✓" : "");

        li.appendChild(bar);
        li.appendChild(label);
        ul.appendChild(li);
    });

    if (optionsWrapper) {
        optionsWrapper.replaceWith(ul);
    }

    var countEl = container.querySelector(".poll-vote-count");
    if (countEl) {
        countEl.textContent = data.total_votes + " oy";
    }

    requestAnimationFrame(function () {
        var bars = ul.querySelectorAll(".poll-result-bar");
        bars.forEach(function (bar, index) {
            bar.style.width = data.results[index].percent + "%";
        });
    });
}

function setupVoteForms() {
    document.addEventListener("submit", function (event) {
        var form = event.target;
        if (!form.classList || !form.classList.contains("vote-form")) return;

        event.preventDefault();
        var container = form.closest("article");
        if (!container) return;

        fetch(form.action, {
            method: "POST",
            body: new FormData(form),
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": getCookie("csrftoken"),
            },
        })
            .then(function (response) {
                return response.json().then(function (data) {
                    return { ok: response.ok, status: response.status, data: data };
                });
            })
            .then(function (result) {
                if (result.data.ok || result.status === 409) {
                    renderPollResults(container, result.data);
                }
                if (!result.data.ok) {
                    window.alert(result.data.error || "Bir hata oluştu.");
                }
            })
            .catch(function () {
                window.alert("Bağlantı hatası, lütfen tekrar dene.");
            });
    });
}

function setupToastDismiss() {
    document.querySelectorAll(".toast").forEach(function (toast) {
        setTimeout(function () {
            toast.style.opacity = "0";
            setTimeout(function () {
                toast.remove();
            }, 300);
        }, 4000);
    });
}

document.addEventListener("DOMContentLoaded", function () {
    setupCharCounters();
    setupDynamicOptionFields();
    setupVoteForms();
    setupToastDismiss();
});
