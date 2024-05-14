// this function makes sure that the correct fields are displayed in
// the add assessment form
function load_form() {
  // get the type of assessment (test/assignment)
  let type = document.getElementById("type");
  let val = type.value;

  // fields to hide and show
  let assignment = document.getElementById("assignment_fields");
  let test = document.getElementById("test_fields");
  let lab = document.getElementById("lab_fields");

  // hide and show accordingly
  if (val == "assignment") {
    assignment.classList.remove("hide");
    test.classList.add("hide");
    lab.classList.add("hide");
  } else if (val == "test") {
    test.classList.remove("hide");
    assignment.classList.add("hide");
    lab.classList.add("hide");
  } else if (val == "lab") {
    lab.classList.remove("hide");
    test.classList.add("hide");
    assignment.classList.add("hide");
  }
}
