document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form").forEach(form => {
    form.addEventListener("submit", function(e) {
      let valid = true;

      const name = form.querySelector("[name='name']");
      const barcode = form.querySelector("[name='barcode']");
      const price = form.querySelector("[name='price']");
      const stock = form.querySelector("[name='stock']");

      // Clear old errors
      form.querySelectorAll(".text-danger").forEach(el => el.textContent = "");

      // Product name validation
      if (!/^[A-Za-z\s]+$/.test(name.value)) {
        form.querySelector("#nameError").textContent = "Only letters and spaces allowed.";
        valid = false;
      }

      // Barcode validation
      if (!/^\d+$/.test(barcode.value)) {
        form.querySelector("#barcodeError").textContent = "Barcode must be numbers only.";
        valid = false;
      }

      // Price validation
      if (isNaN(price.value) || price.value <= 0) {
        form.querySelector("#priceError").textContent = "Price must be a positive number.";
        valid = false;
      }

      // Stock validation
      if (!Number.isInteger(Number(stock.value)) || stock.value < 0) {
        form.querySelector("#stockError").textContent = "Stock must be a non-negative integer.";
        valid = false;
      }

      if (!valid) {
        e.preventDefault(); // stop form submission
      }
    });
  });
});

// Price validation
if (!/^\d+(\.\d{1,2})?$/.test(price.value) || parseFloat(price.value) <= 0) {
  form.querySelector("#priceError").textContent =
    "Price must be a positive number with up to 2 decimal places.";
  valid = false;
}

 

