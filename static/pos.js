document.addEventListener("DOMContentLoaded", () => {
  const cartTableBody = document.querySelector("#cartTable tbody");
  const grandTotalEl = document.getElementById("grandTotal");
  let cart = [];

  // Reset Add Product modal
  const addProductModal = document.getElementById("addProductModal"); 
  if (addProductModal) {
    addProductModal.addEventListener("hidden.bs.modal", function () { 
      const form = this.querySelector("form"); 
      if (form) form.reset(); 
    }); 
  }

  // Add to cart
  document.addEventListener("click", (e) => {
    if (e.target.classList.contains("add-to-cart")) {
      const id = e.target.dataset.id;
      const name = e.target.dataset.name;
      const price = parseFloat(e.target.dataset.price);

      let item = cart.find(p => p.id === id);
      if (item) {
        item.qty++;
      } else {
        cart.push({ id, name, price, qty: 1 });
      }
      renderCart();
    }
  });

  // Search
const searchBar = document.getElementById("searchBar");
if (searchBar) {
  searchBar.addEventListener("keyup", function() {
    let filter = this.value.toLowerCase();
    let rows = document.querySelectorAll("#productsTable tr");
    rows.forEach(row => {
      let text = row.textContent.toLowerCase();
      row.style.display = text.includes(filter) ? "" : "none";
    });
  });
}


  // Render cart
  function renderCart() {
    cartTableBody.innerHTML = "";
    let total = 0;

    cart.forEach((item, index) => {
      const row = document.createElement("tr");
      const itemTotal = item.qty * item.price;
      total += itemTotal;

      row.innerHTML = `
        <td>${item.name}</td>
        <td>
          <button class="btn btn-sm btn-secondary decrease" data-index="${index}">-</button>
          ${item.qty}
          <button class="btn btn-sm btn-secondary increase" data-index="${index}">+</button>
        </td>
        <td>${item.price.toFixed(2)}</td>
        <td>${itemTotal.toFixed(2)}</td>
        <td><button class="btn btn-sm btn-danger remove" data-index="${index}">X</button></td>
      `;
      cartTableBody.appendChild(row);
    });

    grandTotalEl.textContent = total.toFixed(2);

    // Increase quantity
    document.querySelectorAll(".increase").forEach(btn => {
      btn.addEventListener("click", () => {
        cart[btn.dataset.index].qty++;
        renderCart();
      });
    });

    // Decrease quantity
    document.querySelectorAll(".decrease").forEach(btn => {
      btn.addEventListener("click", () => {
        if (cart[btn.dataset.index].qty > 1) {
          cart[btn.dataset.index].qty--;
        } else {
          cart.splice(btn.dataset.index, 1);
        }
        renderCart();
      });
    });

    // Remove item
    document.querySelectorAll(".remove").forEach(btn => {
      btn.addEventListener("click", () => {
        cart.splice(btn.dataset.index, 1);
        renderCart();
      });
    });
  }

  // Checkout
  document.getElementById("checkoutBtn").addEventListener("click", () => {
    if (cart.length === 0) {
        alert("Cart is empty!");
        return;
    }

    const customerId = document.getElementById("customer_id").value;

    fetch("/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cart, customer_id: customerId })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
            return;
        }

        const receiptTableBody = document.getElementById("receiptTableBody");
        const receiptGrandTotal = document.getElementById("receiptGrandTotal");
        const receiptId = document.getElementById("receiptId");
        const receiptCustomer = document.getElementById("receiptCustomer");

        receiptTableBody.innerHTML = "";
        cart.forEach(item => {
            const row = document.createElement("tr");
            const itemTotal = item.qty * item.price;
            row.innerHTML = `
              <td>${item.name}</td>
              <td>${item.qty}</td>
              <td>${item.price.toFixed(2)}</td>
              <td>${itemTotal.toFixed(2)}</td>
            `;
            receiptTableBody.appendChild(row);
        });

        receiptGrandTotal.textContent = data.total.toFixed(2);
        receiptId.textContent = data.receipt_id;
        receiptCustomer.textContent = data.customer_name;
        document.getElementById("receiptCashier").textContent = data.cashier_name;
        document.getElementById("receiptTimestamp").textContent = data.timestamp;
        const receiptModal = new bootstrap.Modal(document.getElementById("receiptModal"));
        receiptModal.show();

        cart = [];
        renderCart();
    });
  });

  // Print receipt
  const printBtn = document.getElementById("printReceiptBtn");
  if (printBtn) {
    printBtn.addEventListener("click", () => {
      const receiptContent = document.getElementById("receiptModal").querySelector(".modal-body").innerHTML;
      const printWindow = window.open("", "", "width=800,height=600");
      printWindow.document.write(`
        <html>
          <head>
            <title>Receipt</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
          </head>
          <body>
            <h2>Receipt</h2>
            ${receiptContent}
          </body>
        </html>
      `);
      printWindow.document.close();
      printWindow.print();
    });
  }

});