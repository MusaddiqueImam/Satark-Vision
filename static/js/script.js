// Function to show a confirmation alert for delete
function confirmDelete(companyName, companyId) {
    if (confirm(`Are you sure you want to delete ${companyName}?`)) {
      window.location.href = `/delete-company/${companyId}`;
    }
  }

// Function to show a confirmation alert for deleting caller
function confirmCallerDelete(callerName, callerId) {
  if (confirm(`Are you sure you want to delete ${callerName}?`)) {
    window.location.href = `/delete-caller/${callerId}`;
  }
}

// Function to show a snackbar notification
function showSnackbar(message) {
var snackbar = document.getElementById("snackbar");
if(snackbar)
    snackbar.textContent = message;
    snackbar.className = "show";
    setTimeout(function () {
        snackbar.className = snackbar.className.replace("show", "");
    }, 3000); // 3 seconds (adjust as needed)
}
