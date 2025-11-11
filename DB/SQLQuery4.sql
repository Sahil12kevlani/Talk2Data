USE FoodDB;
GO

-- ============================================
-- 🔥 SAFE CLEAN REBUILD SCRIPT (RUN ANYTIME)
-- ============================================

-- 1️⃣ Drop dependent tables in correct order
IF OBJECT_ID('dish_ingredients', 'U') IS NOT NULL DROP TABLE dish_ingredients;
IF OBJECT_ID('nutrition_info', 'U') IS NOT NULL DROP TABLE nutrition_info;
IF OBJECT_ID('dishes', 'U') IS NOT NULL DROP TABLE dishes;
IF OBJECT_ID('ingredients', 'U') IS NOT NULL DROP TABLE ingredients;
IF OBJECT_ID('cuisines', 'U') IS NOT NULL DROP TABLE cuisines;
GO

-- ============================================
-- 2️⃣ Create and populate cuisines
-- ============================================
CREATE TABLE cuisines (
    CuisineID INT PRIMARY KEY IDENTITY(1,1),
    CuisineName VARCHAR(100) NOT NULL
);
GO

INSERT INTO cuisines (CuisineName)
VALUES ('Indian'), ('Chinese'), ('Italian'), ('Mexican');
GO

-- ============================================
-- 3️⃣ Create and populate dishes
-- ============================================
CREATE TABLE dishes (
    DishID INT PRIMARY KEY IDENTITY(1,1),
    DishName VARCHAR(100) NOT NULL,
    CuisineID INT,
    Description VARCHAR(255),
    Price DECIMAL(6,2),
    FOREIGN KEY (CuisineID) REFERENCES cuisines(CuisineID)
);
GO

INSERT INTO dishes (DishName, CuisineID, Description, Price)
VALUES
('Paneer Butter Masala', 1, 'Creamy tomato-based curry with paneer cubes.', 250.00),
('Veg Hakka Noodles', 2, 'Stir-fried noodles with vegetables and soy sauce.', 180.00),
('Margherita Pizza', 3, 'Classic pizza with tomato sauce and mozzarella.', 300.00),
('Tacos', 4, 'Corn tortillas filled with veggies and cheese.', 220.00);
GO

-- ============================================
-- 4️⃣ Create and populate ingredients
-- ============================================
CREATE TABLE ingredients (
    IngredientID INT PRIMARY KEY IDENTITY(1,1),
    IngredientName VARCHAR(100) NOT NULL
);
GO

INSERT INTO ingredients (IngredientName)
VALUES
('Paneer'), ('Tomato'), ('Butter'), ('Noodles'), ('Vegetables'),
('Cheese'), ('Tortilla'), ('Sauce');
GO

-- ============================================
-- 5️⃣ Create and populate dish_ingredients mapping
-- ============================================
CREATE TABLE dish_ingredients (
    DishID INT,
    IngredientID INT,
    PRIMARY KEY (DishID, IngredientID),
    FOREIGN KEY (DishID) REFERENCES dishes(DishID),
    FOREIGN KEY (IngredientID) REFERENCES ingredients(IngredientID)
);
GO

INSERT INTO dish_ingredients (DishID, IngredientID)
VALUES
(1, 1), (1, 2), (1, 3),
(2, 4), (2, 5),
(3, 2), (3, 6),
(4, 7), (4, 5), (4, 8);
GO

-- ============================================
-- 6️⃣ Create and populate nutrition_info
-- ============================================
CREATE TABLE nutrition_info (
    NutritionID INT PRIMARY KEY IDENTITY(1,1),
    DishID INT,
    Calories INT,
    Protein DECIMAL(5,2),
    Carbs DECIMAL(5,2),
    Fat DECIMAL(5,2),
    FOREIGN KEY (DishID) REFERENCES dishes(DishID)
);
GO

INSERT INTO nutrition_info (DishID, Calories, Protein, Carbs, Fat)
VALUES
(1, 420, 15.5, 25.3, 28.1),
(2, 320, 8.2, 45.6, 10.3),
(3, 500, 20.1, 60.2, 18.4),
(4, 380, 12.0, 40.0, 14.5);
GO

-- ============================================
-- 7️⃣ Verify all data
-- ============================================
SELECT * FROM cuisines;
SELECT * FROM dishes;
SELECT * FROM ingredients;
SELECT * FROM dish_ingredients;
SELECT * FROM nutrition_info;
GO


USE FoodDB;
GO

-- === Add new cuisines ===
INSERT INTO cuisines (CuisineName)
VALUES ('Thai'), ('American');
GO

-- === Add new dishes ===
INSERT INTO dishes (DishName, CuisineID, Description, Price)
VALUES
('Pad Thai', 5, 'Stir-fried rice noodles with tofu, peanuts, and tamarind sauce.', 280.00),
('Veg Burger', 6, 'Grilled vegetable patty with cheese and lettuce.', 200.00);
GO

-- === Add new ingredients ===
INSERT INTO ingredients (IngredientName)
VALUES ('Tofu'), ('Peanuts'), ('Tamarind Sauce'), ('Burger Bun'), ('Lettuce'), ('Veg Patty');
GO

-- === Map new dish ingredients ===
INSERT INTO dish_ingredients (DishID, IngredientID)
VALUES
(5, 9), (5, 10), (5, 11),  -- Pad Thai
(6, 12), (6, 13), (6, 14); -- Veg Burger
GO

-- === Add nutrition info for new dishes ===
INSERT INTO nutrition_info (DishID, Calories, Protein, Carbs, Fat)
VALUES
(5, 450, 16.5, 55.2, 15.3),  -- Pad Thai
(6, 380, 12.3, 40.0, 18.0);  -- Veg Burger
GO

-- Table: customer_reviews
CREATE TABLE customer_reviews (
    ReviewID INT IDENTITY(1,1) PRIMARY KEY,
    DishID INT,
    Rating INT CHECK (Rating BETWEEN 1 AND 5),
    ReviewText NVARCHAR(255),
    ReviewDate DATETIME DEFAULT GETDATE()
);

-- Insert sample data
INSERT INTO customer_reviews (DishID, Rating, ReviewText)
VALUES
(1, 5, 'Delicious and authentic taste!'),
(3, 4, 'Tasty but could use more cheese.'),
(6, 3, 'Average burger, needs improvement.');
