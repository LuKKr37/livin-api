# =====================================================================
# API DE LIVIN POPAYÁN - Versión 2.0 (Cálculo Corregido)
# Este archivo crea un pequeño servidor web (API) con una única función:
# verificar la disponibilidad y calcular el precio de los apartamentos.
# =====================================================================

# --- PASO 1: LOS INGREDIENTES (Importar las librerías necesarias) ---
import os
import psycopg2
from flask import Flask, request, jsonify
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

# --- PASO 2: LA PREPARACIÓN (Configurar la aplicación y la conexión a la BD) ---

# Creamos la aplicación web con Flask
app = Flask(__name__)

# Función para conectarse a la base de datos de PostgreSQL
# Usará las "variables de entorno" que configuraremos en Easypanel para seguridad
def get_db_connection():
    conn = psycopg2.connect(
        host=os.environ.get('DB_HOST'),
        database=os.environ.get('DB_NAME'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASS')
    )
    return conn

# --- PASO 3: LA RECETA PRINCIPAL (Nuestra primera habilidad para LUIS) ---

# Definimos una "ruta" o "endpoint". Cuando visitemos la URL de nuestro servidor
# seguida de "/check_availability", se ejecutará esta función.
@app.route('/check_availability', methods=)
def check_availability_and_price():
    # 1. Obtener los datos que nos envía el agente (o nosotros para probar)
    start_date_str = request.args.get('start_date') # ej: '2025-10-20'
    end_date_str = request.args.get('end_date')     # ej: '2025-11-15'
    num_bedrooms = request.args.get('num_bedrooms', type=int) # ej: 1

    # Validar que los datos necesarios llegaron
    if not start_date_str or not end_date_str or not num_bedrooms:
        return jsonify({"error": "Faltan parámetros: se requiere start_date, end_date y num_bedrooms"}), 400

    try:
        # 2. Calcular el número de noches de la estadía
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        stay_duration_nights = (end_date - start_date).days

        # Si la duración es menor a la mínima posible (4 noches), no buscamos nada.
        if stay_duration_nights < 4:
            return jsonify() # Devolvemos una lista vacía

        conn = get_db_connection()
        cur = conn.cursor()

        # 3. Construir la consulta SQL para encontrar apartamentos disponibles
        # (Esta sección no ha sido modificada)
        sql_query = """
            SELECT
                p.id,
                p.name,
                p.description,
                pr.price_per_night,
                pr.monthly_rate
            FROM
                properties p
            LEFT JOIN
                pricing_rules pr ON p.pricing_category = pr.category
            WHERE
                p.num_bedrooms = %s
                AND p.min_stay_nights <= %s
                AND (
                    (pr.min_nights <= %s AND pr.max_nights >= %s AND pr.monthly_rate IS NULL) -- Regla por noche
                    OR
                    (%s >= 30 AND pr.monthly_rate IS NOT NULL AND pr.min_nights >= 30) -- Regla mensual
                )
                AND p.id NOT IN (
                    SELECT b.property_id
                    FROM bookings b
                    WHERE b.start_date < %s AND b.end_date > %s
                )
            ORDER BY
                p.id;
        """

        # Ejecutar la consulta con los parámetros de forma segura
        cur.execute(sql_query, (
            num_bedrooms,
            stay_duration_nights,
            stay_duration_nights, stay_duration_nights, # Para la regla por noche
            stay_duration_nights, # Para la regla mensual
            end_date_str, start_date_str # Para la subconsulta de bookings
        ))

        available_properties = cur.fetchall()
        cur.close()
        conn.close()

        # ##################################################################
        # ### INICIO DEL FRAGMENTO MODIFICADO ###
        # ##################################################################

        # 4. Formatear los resultados para que el agente los entienda
        results =
        for prop in available_properties:
            prop_id, name, description, price_per_night, monthly_rate = prop
            total_price = Decimal('0')

            # Calcular el precio total basado en si es tarifa mensual o por noche
            if stay_duration_nights >= 30 and monthly_rate is not None:
                # Lógica mejorada para meses + días restantes
                monthly_rate_dec = Decimal(monthly_rate)
                num_months = stay_duration_nights // 30
                remaining_days = stay_duration_nights % 30
                
                # Precio por los meses completos
                total_price = num_months * monthly_rate_dec
                
                # Si hay días restantes, calcular su costo proporcional
                if remaining_days > 0:
                    # Calculamos el precio por día basado en la tarifa mensual
                    daily_rate = monthly_rate_dec / Decimal('30')
                    total_price += remaining_days * daily_rate
            
            elif price_per_night is not None:
                # Lógica para estadías cortas (sin cambios)
                total_price = stay_duration_nights * Decimal(price_per_night)

            if total_price > 0:
                # Redondear el precio final a 0 decimales para pesos colombianos
                final_price = total_price.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
                
                results.append({
                    "property_id": prop_id,
                    "name": name,
                    "description": description,
                    "monthly_rate": float(monthly_rate) if monthly_rate else None, # Añadimos la tarifa mensual
                    "total_price": float(final_price) # Devolvemos el precio total corregido
                })
        
        # ##################################################################
        # ### FIN DEL FRAGMENTO MODIFICADO ###
        # ##################################################################

        return jsonify(results)

    except Exception as e:
        # Si algo sale mal, devolvemos un error para poder depurarlo
        return jsonify({"error": "Ocurrió un error en el servidor", "details": str(e)}), 500

# --- PASO 4: CÓDIGO PARA PROBAR (Opcional, para ejecutar localmente) ---
if __name__ == '__main__':
    # Esto permite ejecutar el servidor de prueba directamente desde la terminal
    # Necesitarás definir las variables de entorno para que funcione
    app.run(debug=True, port=5001)
