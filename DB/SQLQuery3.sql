CREATE TABLE menu_item_dish_mapping (
    FoodProgram VARCHAR(100),
    ItemCode VARCHAR(20),
    ItemName VARCHAR(100),
    FoodProgramType VARCHAR(50),
    ItemDietCategory VARCHAR(50),
    ItemDishCategory VARCHAR(50),
    DishName VARCHAR(100),
    DishPortionUOM VARCHAR(10),
    DishPortionSize INT,
    DishWtPc INT,
    CMPSectorCode VARCHAR(20),
    PRIMARY KEY (ItemCode, DishName)
);

INSERT INTO menu_item_dish_mapping VALUES
('North Thali', 'ITM001', 'North Thali', 'Veg', 'Vegetarian', 'Main Course', 'Paneer Butter Masala', 'g', 200, 200, 'CMP001'),
('North Thali', 'ITM001', 'North Thali', 'Veg', 'Vegetarian', 'Main Course', 'Roti', 'pcs', 2, 60, 'CMP001'),
('South Thali', 'ITM002', 'South Thali', 'Veg', 'Vegetarian', 'Main Course', 'Sambhar', 'ml', 150, 150, 'CMP002'),
('South Thali', 'ITM002', 'South Thali', 'Veg', 'Vegetarian', 'Main Course', 'Vada', 'pcs', 2, 80, 'CMP002'),
('North Thali', 'ITM001', 'North Thali', 'Veg', 'Vegetarian', 'Main Course', 'Rice', 'g', 150, 150, 'CMP001');


CREATE TABLE dish_master (
    DishCode VARCHAR(20) PRIMARY KEY,
    DishName VARCHAR(100),
    DishCategoryCode VARCHAR(20),
    DishCategoryName VARCHAR(50),
    RecipeCode VARCHAR(20),
    RecipeName VARCHAR(100),
    DishCateogryName VARCHAR(50),
    CMPSectorCode VARCHAR(20)
);

INSERT INTO dish_master VALUES
('D001', 'Paneer Butter Masala', 'DC001', 'Curry', 'R001', 'Paneer Butter Recipe', 'Curry', 'CMP001'),
('D002', 'Roti', 'DC002', 'Bread', 'R002', 'Roti Recipe', 'Bread', 'CMP001'),
('D003', 'Sambhar', 'DC003', 'Curry', 'R003', 'Sambhar Recipe', 'Curry', 'CMP002'),
('D004', 'Vada', 'DC004', 'Snack', 'R004', 'Vada Recipe', 'Snack', 'CMP002'),
('D005', 'Rice', 'DC005', 'Staple', 'R005', 'Rice Recipe', 'Staple', 'CMP001');


CREATE TABLE recipe_mog_mapping (
    DishCode VARCHAR(20),
    DishName VARCHAR(100),
    RecipeCode VARCHAR(20),
    RecipeName VARCHAR(100),
    DishCategoryCode VARCHAR(20),
    DishCategoryName VARCHAR(50),
    DietCategoryName VARCHAR(50),
    MOGCode VARCHAR(20),
    MOGName VARCHAR(100),
    MOGQty INT,
    CMPSectorCode VARCHAR(20),
    PRIMARY KEY (DishCode, MOGCode),
    FOREIGN KEY (DishCode) REFERENCES dish_master(DishCode)
);

INSERT INTO recipe_mog_mapping VALUES
('D001', 'Paneer Butter Masala', 'R001', 'Paneer Butter Recipe', 'DC001', 'Curry', 'Vegetarian', 'M001', 'Paneer', 100, 'CMP001'),
('D001', 'Paneer Butter Masala', 'R001', 'Paneer Butter Recipe', 'DC001', 'Curry', 'Vegetarian', 'M002', 'Butter', 50, 'CMP001'),
('D002', 'Roti', 'R002', 'Roti Recipe', 'DC002', 'Bread', 'Vegetarian', 'M003', 'Wheat Flour', 120, 'CMP001'),
('D003', 'Sambhar', 'R003', 'Sambhar Recipe', 'DC003', 'Curry', 'Vegetarian', 'M004', 'Lentils', 80, 'CMP002'),
('D004', 'Vada', 'R004', 'Vada Recipe', 'DC004', 'Snack', 'Vegetarian', 'M005', 'Urad Dal', 90, 'CMP002'),
('D005', 'Rice', 'R005', 'Rice Recipe', 'DC005', 'Staple', 'Vegetarian', 'M006', 'Rice Grains', 150, 'CMP001');


CREATE TABLE mog_article_mapping (
    MOGCode VARCHAR(20) PRIMARY KEY,
    MOGName VARCHAR(100),
    ArticleNumber VARCHAR(20),
    ArticleDescription VARCHAR(200)
);

INSERT INTO mog_article_mapping VALUES
('M001', 'Paneer', 'A001', 'Amul Malai Paneer 100gm'),
('M002', 'Butter', 'A002', 'Amul Salted Butter 100gm'),
('M003', 'Wheat Flour', 'A003', 'Ashirvad whole wheat 5kg'),
('M004', 'Lentils', 'A004', 'UB 1kg'),
('M005', 'Urad Dal', 'A005', 'UB 1kg'),
('M006', 'Rice Grains', 'A006', 'Kohinoor 5kg');

-- ✅ Correct foreign key (reverse direction)
ALTER TABLE recipe_mog_mapping
ADD CONSTRAINT fk_recipe_mog
FOREIGN KEY (MOGCode) REFERENCES mog_article_mapping(MOGCode);

CREATE TABLE supplier_master (
    SupplierID VARCHAR(10) PRIMARY KEY,
    SupplierName VARCHAR(100),
    ContactNumber VARCHAR(15),
    Location VARCHAR(100),
    ArticleNumber VARCHAR(10)    
);

INSERT INTO supplier_master (SupplierID, SupplierName, ContactNumber, Location, ArticleNumber)
VALUES
('S001', 'FreshFarm Foods', '9876543210', 'Mumbai', 'A001'),
('S002', 'DairyDelight Pvt Ltd', '9823456789', 'Pune', 'A002'),
('S003', 'GrainMasters Ltd', '9898765432', 'Nagpur', 'A003'),
('S004', 'RiceWorld Traders', '9123456780', 'Nashik', 'A006');


SELECT * FROM supplier_master;


 SELECT SupplierID FROM supplier_master WHERE SupplierName like '%Fresh%'
  SELECT SupplierID FROM supplier_master WHERE SupplierName like '%Farm%'
   SELECT SupplierID FROM supplier_master WHERE SupplierName like '%Foods%'

   SELECT SupplierID, SupplierName, ContactNumber, Location, ArticleNumber FROM supplier_master;
