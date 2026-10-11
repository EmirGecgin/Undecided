document.addEventListener("DOMContentLoaded", function () {
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
});
