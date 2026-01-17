# gastro_calc.py
# Gastro-Kalkulations-Tool MVP+ mit Recipe-Dependencies
# Python 3.12

import sqlite3
from typing import Dict, List, Tuple, Optional

# ============================================================
# CORE CALCULATION FUNCTIONS
# ============================================================

def calc_cost_per_liter(ingredients_cost: float, energy_cost: float, 
                        batch_size_l: float, yield_pct: float) -> float:
    """Berechnet die Kosten pro Netto-Liter Masse."""
    if batch_size_l <= 0 or yield_pct <= 0:
        return 0.0
    net_output = batch_size_l * (yield_pct / 100)
    return (ingredients_cost + energy_cost) / net_output

def calc_cost_per_unit(cost_per_liter: float, size_l: float, 
                       price_jar: float, price_lid: float, price_label: float) -> float:
    """Berechnet die Herstellkosten pro abgefüllter Einheit."""
    return (cost_per_liter * size_l) + price_jar + price_lid + price_label

def calc_target_price(cost_per_unit: float, markup_factor: float) -> float:
    """Berechnet den Brutto-Verkaufspreis mit Schweizer Rappenrundung."""
    base = cost_per_unit * markup_factor
    return round(base * 20) / 20

# ============================================================
# DATABASE & RECURSIVE CALCULATION
# ============================================================

class GastroCalculator:
    def __init__(self, db_path: str = "gastro.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._recipe_cache: Dict[int, Tuple[float, Dict]] = {}
    
    def calculate_recipe_cost(self, recipe_id: int, depth: int = 0) -> Tuple[float, Dict]:
        """
        Rekursive Berechnung der Rezeptkosten.
        Gibt zurück: (cost_per_liter, details_dict)
        """
        if depth > 3:
            raise RecursionError(f"Max Verschachtelungstiefe überschritten bei Recipe {recipe_id}")
        
        # Cache prüfen
        if recipe_id in self._recipe_cache:
            return self._recipe_cache[recipe_id]
        
        cursor = self.conn.cursor()
        
        # Recipe-Daten holen
        recipe = cursor.execute(
            "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
        ).fetchone()
        
        if not recipe:
            raise ValueError(f"Recipe {recipe_id} nicht gefunden")
        
        # Recipe-Items holen
        items = cursor.execute(
            "SELECT * FROM recipe_items WHERE recipe_id = ?", (recipe_id,)
        ).fetchall()
        
        total_material_cost = 0.0
        details = {
            'name': recipe['name'],
            'batch_size': recipe['batch_size_l'],
            'yield_pct': recipe['yield_pct'],
            'level': recipe['level'],
            'ingredients': [],
            'sub_recipes': []
        }
        
        # Items durchgehen
        for item in items:
            amount = item['amount']
            
            if item['ingredient_id']:
                # Rohstoff
                ing = cursor.execute(
                    "SELECT * FROM ingredients WHERE id = ?", (item['ingredient_id'],)
                ).fetchone()
                
                cost = amount * ing['price_per_unit']
                total_material_cost += cost
                
                details['ingredients'].append({
                    'name': ing['name'],
                    'amount': amount,
                    'unit': ing['unit'],
                    'price_per_unit': ing['price_per_unit'],
                    'cost': cost
                })
            
            elif item['sub_recipe_id']:
                # Sub-Recipe (rekursiv berechnen)
                sub_cost_per_liter, sub_details = self.calculate_recipe_cost(
                    item['sub_recipe_id'], depth + 1
                )
                
                cost = amount * sub_cost_per_liter
                total_material_cost += cost
                
                details['sub_recipes'].append({
                    'recipe_id': item['sub_recipe_id'],
                    'name': sub_details['name'],
                    'amount_l': amount,
                    'cost_per_liter': sub_cost_per_liter,
                    'cost': cost
                })
        
        # Energie addieren
        energy_cost = recipe['energy_cost_chf']
        total_cost = total_material_cost + energy_cost
        
        # Kosten pro Liter berechnen
        cost_per_liter = calc_cost_per_liter(
            total_material_cost, energy_cost, 
            recipe['batch_size_l'], recipe['yield_pct']
        )
        
        details['energy_cost'] = energy_cost
        details['total_material_cost'] = total_material_cost
        details['total_cost'] = total_cost
        details['net_output_l'] = recipe['batch_size_l'] * (recipe['yield_pct'] / 100)
        details['cost_per_liter'] = cost_per_liter
        
        # Cache speichern (cost_per_liter und details)
        self._recipe_cache[recipe_id] = (cost_per_liter, details)
        
        return cost_per_liter, details
    
    def calculate_product(self, product_id: int) -> Dict:
        """Berechnet einen fertigen Verkaufsartikel."""
        cursor = self.conn.cursor()
        
        product = cursor.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        
        if not product:
            raise ValueError(f"Product {product_id} nicht gefunden")
        
        # Recipe-Kosten holen
        cost_per_liter, recipe_details = self.calculate_recipe_cost(product['recipe_id'])
        
        # Verpackung holen
        packaging = cursor.execute(
            "SELECT * FROM packaging_types WHERE id = ?", (product['packaging_id'],)
        ).fetchone()
        
        # Stückkosten berechnen
        cost_per_unit = calc_cost_per_unit(
            cost_per_liter, packaging['size_l'],
            packaging['price_jar'], packaging['price_lid'], packaging['price_label']
        )
        
        # Zielpreis berechnen
        target_price = calc_target_price(cost_per_unit, product['markup_factor'])
        
        # Margen berechnen
        brutto_margin_pct = ((target_price - cost_per_unit) / target_price) * 100
        
        return {
            'product_id': product_id,
            'recipe_name': recipe_details['name'],
            'packaging_name': packaging['name'],
            'size_l': packaging['size_l'],
            'recipe_cost_per_liter': cost_per_liter,
            'packaging_cost': packaging['price_jar'] + packaging['price_lid'] + packaging['price_label'],
            'cost_per_unit': cost_per_unit,
            'markup_factor': product['markup_factor'],
            'target_price': target_price,
            'brutto_margin_pct': brutto_margin_pct,
            'recipe_details': recipe_details
        }
    
    def print_product_calculation(self, product_id: int):
        """Formatierte Ausgabe einer Produkt-Kalkulation."""
        result = self.calculate_product(product_id)
        
        print(f"\n{'='*80}")
        print(f"PRODUKT-KALKULATION: {result['recipe_name']} in {result['packaging_name']}")
        print(f"{'='*80}")
        
        # Recipe-Details
        rd = result['recipe_details']
        print(f"\nREZEPTUR (Level {rd['level']}):")
        print(f"├─ Ansatz: {rd['batch_size']:.1f}L → Netto: {rd['net_output_l']:.1f}L ({rd['yield_pct']:.0f}%)")
        
        if rd['ingredients']:
            print(f"├─ Rohstoffe:")
            for ing in rd['ingredients']:
                print(f"│  ├─ {ing['name']}: {ing['amount']:.2f} {ing['unit']} @ {ing['price_per_unit']:.2f} = {ing['cost']:.2f} CHF")
        
        if rd['sub_recipes']:
            print(f"├─ Sub-Rezepte:")
            for sub in rd['sub_recipes']:
                print(f"│  ├─ {sub['name']}: {sub['amount_l']:.1f}L @ {sub['cost_per_liter']:.2f}/L = {sub['cost']:.2f} CHF")
        
        print(f"├─ Energie: {rd['energy_cost']:.2f} CHF")
        print(f"└─ KOSTEN/LITER: {rd['cost_per_liter']:.2f} CHF")
        
        # Produkt-Kalkulation
        print(f"\nVERKAUFSEINHEIT ({result['size_l']*1000:.0f}ml):")
        print(f"├─ Masse: {result['size_l']:.3f}L × {result['recipe_cost_per_liter']:.2f} = {result['size_l'] * result['recipe_cost_per_liter']:.2f} CHF")
        print(f"├─ Verpackung: {result['packaging_cost']:.2f} CHF")
        print(f"├─ HERSTELLKOSTEN: {result['cost_per_unit']:.2f} CHF")
        print(f"├─ Faktor: {result['markup_factor']:.1f}x")
        print(f"├─ ZIELPREIS: {result['target_price']:.2f} CHF")
        print(f"└─ Brutto-Marge: {result['brutto_margin_pct']:.1f}%")
        print(f"{'='*80}\n")
    
    def close(self):
        self.conn.close()

# ============================================================
# DATABASE SETUP
# ============================================================

def setup_database(db_path: str = "gastro.db"):
    """Erstellt die Datenbank mit Schema und Test-Daten."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Schema erstellen
    cursor.executescript("""
    DROP TABLE IF EXISTS products;
    DROP TABLE IF EXISTS recipe_items;
    DROP TABLE IF EXISTS recipes;
    DROP TABLE IF EXISTS packaging_types;
    DROP TABLE IF EXISTS ingredients;
    
    CREATE TABLE ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        unit TEXT NOT NULL CHECK(unit IN ('kg', 'l')),
        price_per_unit REAL NOT NULL CHECK(price_per_unit >= 0),
        supplier TEXT,
        last_update DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE packaging_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        size_l REAL NOT NULL CHECK(size_l > 0),
        price_jar REAL NOT NULL CHECK(price_jar >= 0),
        price_lid REAL NOT NULL CHECK(price_lid >= 0),
        price_label REAL NOT NULL CHECK(price_label >= 0)
    );
    
    CREATE TABLE recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        batch_size_l REAL NOT NULL CHECK(batch_size_l > 0),
        energy_cost_chf REAL NOT NULL CHECK(energy_cost_chf >= 0),
        yield_pct REAL NOT NULL CHECK(yield_pct > 0 AND yield_pct <= 100),
        level INTEGER DEFAULT 1 CHECK(level <= 3)
    );
    
    CREATE TABLE recipe_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipe_id INTEGER NOT NULL,
        ingredient_id INTEGER,
        sub_recipe_id INTEGER,
        amount REAL NOT NULL CHECK(amount > 0),
        FOREIGN KEY (recipe_id) REFERENCES recipes(id),
        FOREIGN KEY (ingredient_id) REFERENCES ingredients(id),
        FOREIGN KEY (sub_recipe_id) REFERENCES recipes(id),
        CHECK (
            (ingredient_id IS NOT NULL AND sub_recipe_id IS NULL) OR
            (ingredient_id IS NULL AND sub_recipe_id IS NOT NULL)
        )
    );
    
    CREATE TABLE products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipe_id INTEGER NOT NULL,
        packaging_id INTEGER NOT NULL,
        markup_factor REAL NOT NULL CHECK(markup_factor >= 1.0 AND markup_factor <= 10.0),
        FOREIGN KEY (recipe_id) REFERENCES recipes(id),
        FOREIGN KEY (packaging_id) REFERENCES packaging_types(id)
    );
    
    CREATE INDEX idx_recipe_items_recipe ON recipe_items(recipe_id);
    CREATE INDEX idx_recipe_items_ingredient ON recipe_items(ingredient_id);
    CREATE INDEX idx_recipe_items_subrecipe ON recipe_items(sub_recipe_id);
    """)
    
    # Test-Daten einfügen
    cursor.executescript("""
    -- Rohstoffe
    INSERT INTO ingredients (name, unit, price_per_unit, supplier) VALUES
    ('Kalbsknochen', 'kg', 1.50, 'Transgourmet'),
    ('Mirepoix-Gemüse', 'kg', 3.33, 'Prodega'),
    ('Weisswein', 'l', 7.00, 'Rahm'),
    ('Tomatenpüree', 'kg', 4.50, 'Transgourmet'),
    ('Cognac', 'l', 45.00, 'Rahm'),
    ('Schalotten', 'kg', 8.00, 'Prodega'),
    ('Morcheln getrocknet', 'kg', 380.00, 'Delikatessen AG'),
    ('Portwein', 'l', 22.00, 'Rahm');
    
    -- Verpackungen (Glaspreis aus Screenshot + Etikette 0.60)
    INSERT INTO packaging_types (name, size_l, price_jar, price_lid, price_label) VALUES
    ('Weck-Glas 110ml', 0.110, 1.05, 0.00, 0.60),
    ('Weck-Glas 245ml', 0.245, 1.38, 0.00, 0.60),
    ('Weck-Glas 435ml', 0.435, 1.58, 0.00, 0.60),
    ('Weck-Glas 795ml', 0.795, 2.57, 0.00, 0.60);
    
    -- Rezepturen
    INSERT INTO recipes (name, batch_size_l, energy_cost_chf, yield_pct, level) VALUES
    ('Grundfond Kalb', 100.0, 8.00, 60.0, 1),
    ('Demi-Glace Classique', 50.0, 4.80, 45.0, 2),
    ('Sauce Périgueux', 10.0, 1.60, 90.0, 3);
    
    -- Grundfond: Nur Ingredients
    INSERT INTO recipe_items (recipe_id, ingredient_id, sub_recipe_id, amount) VALUES
    (1, 1, NULL, 100.0),
    (1, 2, NULL, 30.0),
    (1, 3, NULL, 20.0);
    
    -- Demi-Glace: Grundfond + Ingredients
    INSERT INTO recipe_items (recipe_id, ingredient_id, sub_recipe_id, amount) VALUES
    (2, NULL, 1, 50.0),
    (2, 4, NULL, 5.0),
    (2, 5, NULL, 0.5);
    
    -- Sauce Périgueux: Demi-Glace + Luxus-Zutaten
    INSERT INTO recipe_items (recipe_id, ingredient_id, sub_recipe_id, amount) VALUES
    (3, NULL, 2, 10.0),
    (3, 6, NULL, 0.5),
    (3, 7, NULL, 0.1),
    (3, 8, NULL, 1.5);
    
    -- Produkte
    INSERT INTO products (recipe_id, packaging_id, markup_factor) VALUES
    (1, 2, 3.8),  -- Grundfond 245ml
    (2, 2, 5.2),  -- Demi-Glace 245ml
    (3, 2, 6.5),  -- Sauce Périgueux 245ml
    (2, 4, 4.0);  -- Demi-Glace 795ml
    """)
    
    conn.commit()
    conn.close()
    print(f"Datenbank '{db_path}' erfolgreich erstellt.")

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    # Datenbank erstellen
    setup_database()
    
    # Calculator initialisieren
    calc = GastroCalculator()
    
    # Alle Produkte kalkulieren
    for product_id in [1, 2, 3, 4]:
        calc.print_product_calculation(product_id)
    
    calc.close()
