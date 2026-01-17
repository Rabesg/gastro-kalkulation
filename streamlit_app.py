# streamlit_app.py
# Gastro-Kalkulations-Tool - Web Interface
# Python 3.12 + Streamlit

import streamlit as st
import sqlite3
import pandas as pd
from gastro_calc import GastroCalculator, setup_database
import os

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Gastro Kalkulation",
    page_icon="🍴",
    layout="wide"
)

# ============================================================
# DATABASE INIT
# ============================================================

DB_PATH = "gastro.db"

if not os.path.exists(DB_PATH):
    setup_database(DB_PATH)
    st.success("Datenbank wurde erstellt.")

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_all_ingredients():
    """Holt alle Rohstoffe aus der DB."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM ingredients ORDER BY name", conn)
    conn.close()
    return df

def get_all_recipes():
    """Holt alle Rezepte aus der DB."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM recipes ORDER BY level, name", conn)
    conn.close()
    return df

def get_all_products():
    """Holt alle Produkte mit Details."""
    conn = sqlite3.connect(DB_PATH)
    query = """
    SELECT 
        p.id as product_id,
        r.name as recipe_name,
        r.level,
        pk.name as packaging_name,
        pk.size_l,
        p.markup_factor
    FROM products p
    JOIN recipes r ON p.recipe_id = r.id
    JOIN packaging_types pk ON p.packaging_id = pk.id
    ORDER BY r.level, r.name
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def update_ingredient_price(ingredient_id: int, new_price: float):
    """Aktualisiert den Preis eines Rohstoffs."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE ingredients SET price_per_unit = ?, last_update = CURRENT_TIMESTAMP WHERE id = ?",
        (new_price, ingredient_id)
    )
    conn.commit()
    conn.close()

# ============================================================
# MAIN APP
# ============================================================

st.title("🍴 Gastro-Kalkulations-Tool")
st.markdown("**Manufaktur-Kalkulation mit automatischer Preiskaskade**")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🧮 Kalkulation", "🥕 Rohstoffe", "📝 Rezepte"])

# ============================================================
# TAB 1: DASHBOARD
# ============================================================

with tab1:
    st.header("Produkt-Übersicht")
    
    calc = GastroCalculator(DB_PATH)
    products_df = get_all_products()
    
    # Kalkuliere alle Produkte
    results = []
    for _, row in products_df.iterrows():
        try:
            result = calc.calculate_product(row['product_id'])
            results.append({
                'Produkt': f"{result['recipe_name']} ({result['packaging_name']})",
                'Level': row['level'],
                'Grösse': f"{result['size_l']*1000:.0f}ml",
                'Herstellkosten': f"{result['cost_per_unit']:.2f} CHF",
                'Zielpreis': f"{result['target_price']:.2f} CHF",
                'Marge': f"{result['brutto_margin_pct']:.1f}%",
                'Faktor': f"{result['markup_factor']:.1f}x"
            })
        except Exception as e:
            st.error(f"Fehler bei Produkt {row['product_id']}: {e}")
    
    calc.close()
    
    if results:
        df_results = pd.DataFrame(results)
        st.dataframe(df_results, use_container_width=True, hide_index=True)
        
        # KPIs
        col1, col2, col3 = st.columns(3)
        with col1:
            avg_margin = df_results['Marge'].str.rstrip('%').astype(float).mean()
            st.metric("Ø Marge", f"{avg_margin:.1f}%")
        with col2:
            st.metric("Produkte", len(results))
        with col3:
            levels = df_results['Level'].unique()
            st.metric("Max Level", max(levels))

# ============================================================
# TAB 2: DETAILLIERTE KALKULATION
# ============================================================

with tab2:
    st.header("Detaillierte Kalkulation")
    
    products_df = get_all_products()
    product_options = {
        f"{row['recipe_name']} - {row['packaging_name']} ({row['size_l']*1000:.0f}ml)": row['product_id']
        for _, row in products_df.iterrows()
    }
    
    selected_product_name = st.selectbox("Produkt wählen:", list(product_options.keys()))
    selected_product_id = product_options[selected_product_name]
    
    if st.button("Kalkulation anzeigen", type="primary"):
        calc = GastroCalculator(DB_PATH)
        result = calc.calculate_product(selected_product_id)
        rd = result['recipe_details']
        
        # Rezeptur-Details
        st.subheader(f"Rezeptur: {result['recipe_name']} (Level {rd['level']})")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Ansatz", f"{rd['batch_size']:.1f}L")
        with col2:
            st.metric("Netto-Output", f"{rd['net_output_l']:.1f}L")
        with col3:
            st.metric("Ausbeute", f"{rd['yield_pct']:.0f}%")
        
        # Rohstoffe
        if rd['ingredients']:
            st.markdown("**Rohstoffe:**")
            ing_data = []
            for ing in rd['ingredients']:
                ing_data.append({
                    'Name': ing['name'],
                    'Menge': f"{ing['amount']:.2f} {ing['unit']}",
                    'Preis/Einheit': f"{ing['price_per_unit']:.2f} CHF",
                    'Kosten': f"{ing['cost']:.2f} CHF"
                })
            st.dataframe(pd.DataFrame(ing_data), hide_index=True, use_container_width=True)
        
        # Sub-Rezepte
        if rd['sub_recipes']:
            st.markdown("**Sub-Rezepte:**")
            sub_data = []
            for sub in rd['sub_recipes']:
                sub_data.append({
                    'Name': sub['name'],
                    'Menge': f"{sub['amount_l']:.1f}L",
                    'Preis/Liter': f"{sub['cost_per_liter']:.2f} CHF",
                    'Kosten': f"{sub['cost']:.2f} CHF"
                })
            st.dataframe(pd.DataFrame(sub_data), hide_index=True, use_container_width=True)
        
        # Energie
        st.metric("Energiekosten", f"{rd['energy_cost']:.2f} CHF")
        
        # Masse-Kosten
        st.divider()
        st.metric("🎯 Kosten pro Liter Masse", f"{rd['cost_per_liter']:.2f} CHF", 
                  help="Basis für alle Gebindegrössen")
        
        # Verkaufseinheit
        st.subheader(f"Verkaufseinheit: {result['packaging_name']}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Masse-Anteil", 
                      f"{result['size_l'] * result['recipe_cost_per_liter']:.2f} CHF")
            st.metric("Verpackung", f"{result['packaging_cost']:.2f} CHF")
            st.metric("Herstellkosten", f"{result['cost_per_unit']:.2f} CHF")
        
        with col2:
            st.metric("Markup-Faktor", f"{result['markup_factor']:.1f}x")
            st.metric("Zielpreis", f"{result['target_price']:.2f} CHF")
            st.metric("Brutto-Marge", f"{result['brutto_margin_pct']:.1f}%",
                      delta="Gesund" if result['brutto_margin_pct'] > 70 else "Tief")
        
        calc.close()

# ============================================================
# TAB 3: ROHSTOFF-VERWALTUNG
# ============================================================

with tab3:
    st.header("Rohstoff-Preise verwalten")
    st.markdown("**Preisänderungen wirken sich automatisch auf alle Produkte aus.**")
    
    ingredients_df = get_all_ingredients()
    
    # Preise anzeigen
    st.dataframe(
        ingredients_df[['name', 'unit', 'price_per_unit', 'supplier', 'last_update']],
        column_config={
            'name': 'Rohstoff',
            'unit': 'Einheit',
            'price_per_unit': st.column_config.NumberColumn('Preis/Einheit', format="%.2f CHF"),
            'supplier': 'Lieferant',
            'last_update': 'Letzte Änderung'
        },
        hide_index=True,
        use_container_width=True
    )
    
    # Preis ändern
    st.subheader("Preis ändern")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        ingredient_options = {row['name']: row['id'] for _, row in ingredients_df.iterrows()}
        selected_ingredient = st.selectbox("Rohstoff:", list(ingredient_options.keys()))
    
    with col2:
        current_price = ingredients_df[ingredients_df['name'] == selected_ingredient]['price_per_unit'].values[0]
        st.metric("Aktuell", f"{current_price:.2f} CHF")
    
    with col3:
        new_price = st.number_input("Neuer Preis:", min_value=0.0, value=float(current_price), 
                                     step=0.1, format="%.2f")
    
    if st.button("Preis aktualisieren", type="primary"):
        ingredient_id = ingredient_options[selected_ingredient]
        update_ingredient_price(ingredient_id, new_price)
        st.success(f"✅ Preis für '{selected_ingredient}' auf {new_price:.2f} CHF aktualisiert.")
        st.rerun()

# ============================================================
# TAB 4: REZEPTE
# ============================================================

with tab4:
    st.header("Rezeptur-Übersicht")
    
    recipes_df = get_all_recipes()
    
    st.dataframe(
        recipes_df[['name', 'level', 'batch_size_l', 'energy_cost_chf', 'yield_pct']],
        column_config={
            'name': 'Rezept',
            'level': 'Level',
            'batch_size_l': st.column_config.NumberColumn('Ansatz (L)', format="%.1f"),
            'energy_cost_chf': st.column_config.NumberColumn('Energie (CHF)', format="%.2f"),
            'yield_pct': st.column_config.NumberColumn('Ausbeute (%)', format="%.0f")
        },
        hide_index=True,
        use_container_width=True
    )
    
    st.info("💡 Rezept-Editor kommt in der nächsten Version.")

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("### 🎯 Tool-Info")
    st.markdown("""
    **Features:**
    - ✅ 3-Level-Rezeptur-Kaskade
    - ✅ Automatische Preisanpassung
    - ✅ Rappenrundung (0.05 CHF)
    - ✅ Mehrere Gebindegrössen
    
    **Version:** MVP+ 1.0
    """)
    
    st.divider()
    
    st.markdown("### 📚 Shortcuts")
    st.markdown("""
    - **Dashboard**: Schnelle Übersicht
    - **Kalkulation**: Detailansicht
    - **Rohstoffe**: Preise anpassen
    - **Rezepte**: Übersicht
    """)
