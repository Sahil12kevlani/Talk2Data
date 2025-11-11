-- =========================================
-- 🚀 Create a New Database
-- =========================================
CREATE DATABASE OrdersDB;
GO

USE OrdersDB;
GO

-- =========================================
-- 1️⃣ Customers Table
-- =========================================
CREATE TABLE customers (
    CustomerID INT IDENTITY(1,1) PRIMARY KEY,
    CustomerName VARCHAR(100),
    Email VARCHAR(100),
    Phone VARCHAR(15),
    City VARCHAR(50),
    State VARCHAR(50),
    RegistrationDate DATETIME DEFAULT GETDATE()
);

INSERT INTO customers (CustomerName, Email, Phone, City, State)
VALUES
('Amit Sharma', 'amit.sharma@example.com', '9876543210', 'Mumbai', 'Maharashtra'),
('Riya Patel', 'riya.patel@example.com', '9823456789', 'Pune', 'Maharashtra'),
('Karan Mehta', 'karan.mehta@example.com', '9898765432', 'Delhi', 'Delhi'),
('Neha Verma', 'neha.verma@example.com', '9123456780', 'Bangalore', 'Karnataka');

-- =========================================
-- 2️⃣ Products Table
-- =========================================
CREATE TABLE products (
    ProductID INT IDENTITY(1,1) PRIMARY KEY,
    ProductName VARCHAR(100),
    Category VARCHAR(50),
    UnitPrice DECIMAL(10,2),
    Stock INT,
    SupplierID INT
);

INSERT INTO products (ProductName, Category, UnitPrice, Stock, SupplierID)
VALUES
('Paneer Butter Masala Mix', 'Food', 120.00, 200, 1),
('Whole Wheat Flour', 'Grocery', 80.00, 500, 2),
('Basmati Rice 5kg', 'Grocery', 450.00, 300, 3),
('Olive Oil 1L', 'Grocery', 700.00, 150, 4),
('Green Tea 100g', 'Beverage', 250.00, 100, 5);

-- =========================================
-- 3️⃣ Suppliers Table
-- =========================================
CREATE TABLE suppliers (
    SupplierID INT IDENTITY(1,1) PRIMARY KEY,
    SupplierName VARCHAR(100),
    ContactNumber VARCHAR(15),
    City VARCHAR(50),
    Rating DECIMAL(3,1)
);

INSERT INTO suppliers (SupplierName, ContactNumber, City, Rating)
VALUES
('FreshFarm Foods', '9876543210', 'Mumbai', 4.8),
('GrainMasters Ltd', '9823456789', 'Nagpur', 4.5),
('RiceWorld Traders', '9898765432', 'Nashik', 4.7),
('OilCraft India', '9123456780', 'Surat', 4.6),
('TeaLeaf Pvt Ltd', '9001234567', 'Darjeeling', 4.9);

-- =========================================
-- 4️⃣ Orders Table
-- =========================================
CREATE TABLE orders (
    OrderID INT IDENTITY(1,1) PRIMARY KEY,
    CustomerID INT,
    OrderDate DATETIME DEFAULT GETDATE(),
    TotalAmount DECIMAL(10,2),
    PaymentStatus VARCHAR(20),
    DeliveryStatus VARCHAR(20),
    FOREIGN KEY (CustomerID) REFERENCES customers(CustomerID)
);

INSERT INTO orders (CustomerID, OrderDate, TotalAmount, PaymentStatus, DeliveryStatus)
VALUES
(1, '2025-11-01', 850.00, 'Paid', 'Delivered'),
(2, '2025-11-02', 450.00, 'Pending', 'Processing'),
(3, '2025-11-03', 1200.00, 'Paid', 'Shipped'),
(4, '2025-11-04', 700.00, 'Paid', 'Delivered');

-- =========================================
-- 5️⃣ Order Details Table
-- =========================================
CREATE TABLE order_details (
    OrderDetailID INT IDENTITY(1,1) PRIMARY KEY,
    OrderID INT,
    ProductID INT,
    Quantity INT,
    Subtotal DECIMAL(10,2),
    FOREIGN KEY (OrderID) REFERENCES orders(OrderID),
    FOREIGN KEY (ProductID) REFERENCES products(ProductID)
);

INSERT INTO order_details (OrderID, ProductID, Quantity, Subtotal)
VALUES
(1, 1, 2, 240.00),
(1, 2, 3, 240.00),
(1, 3, 1, 450.00),
(2, 5, 2, 500.00),
(3, 3, 2, 900.00),
(3, 4, 1, 700.00),
(4, 2, 5, 400.00);

-- =========================================
-- 6️⃣ Payments Table
-- =========================================
CREATE TABLE payments (
    PaymentID INT IDENTITY(1,1) PRIMARY KEY,
    OrderID INT,
    PaymentMethod VARCHAR(50),
    TransactionID VARCHAR(50),
    PaymentDate DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (OrderID) REFERENCES orders(OrderID)
);

INSERT INTO payments (OrderID, PaymentMethod, TransactionID, PaymentDate)
VALUES
(1, 'UPI', 'TXN12345', '2025-11-01'),
(3, 'Credit Card', 'TXN12346', '2025-11-03'),
(4, 'Cash on Delivery', 'TXN12347', '2025-11-04');

-- =========================================
-- 7️⃣ Delivery Table
-- =========================================
CREATE TABLE delivery (
    DeliveryID INT IDENTITY(1,1) PRIMARY KEY,
    OrderID INT,
    DeliveryPartner VARCHAR(100),
    DeliveryDate DATETIME,
    DeliveryCity VARCHAR(50),
    FOREIGN KEY (OrderID) REFERENCES orders(OrderID)
);

INSERT INTO delivery (OrderID, DeliveryPartner, DeliveryDate, DeliveryCity)
VALUES
(1, 'Delhivery', '2025-11-02', 'Mumbai'),
(3, 'BlueDart', '2025-11-04', 'Delhi'),
(4, 'Shadowfax', '2025-11-05', 'Bangalore');

-- =========================================
-- ✅ Verification Queries
-- =========================================
SELECT * FROM customers;
SELECT * FROM orders;
SELECT * FROM order_details;
SELECT * FROM payments;
SELECT * FROM delivery;
SELECT * FROM suppliers;
SELECT * FROM products;
GO
