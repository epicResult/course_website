// adjust the height of the navbar according to its contents
window.addEventListener("DOMContentLoaded", function () {
  adjustMargin();
});

// function to adjust the margin of page content
function adjustMargin() {
  const navbarLinks = document.querySelector(".navbar-links");
  const content = document.querySelector(".content");

  // if not logged in
  if (navbarLinks.children.length === 3) {
    content.style.marginTop = "100px"; // Adjust this value as needed
  } else {
    // logged in user
    content.style.minHeight = "100vh";
  }
}
