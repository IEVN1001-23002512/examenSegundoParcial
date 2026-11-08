from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql
from datetime import datetime

app = Flask(__name__)
# Habilita CORS para permitir que Angular (puerto 4200) se comunique con Flask (puerto 5000)
CORS(app) 

# Función para conectar a la base de datos MySQL
def obtener_conexion():
    return pymysql.connect(
        host='localhost',
        user='root', # Pon aquí tu usuario de MySQL (por defecto suele ser root)
        password='', # Pon aquí tu contraseña de MySQL si tienes una
        database='apizzeria',
        cursorclass=pymysql.cursors.DictCursor
    )

# ENDPOINT 1: Guardar un pedido
@app.route('/api/pedidos', methods=['POST'])
def guardar_pedido():
    data = request.json
    cliente = data['cliente']
    pizzas = data['pizzas']
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    try:
        # Insertar los datos del cliente
        sql_cliente = """
            INSERT INTO clientes (nombre_completo, direccion, telefono, fecha_pedido) 
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(sql_cliente, (
            cliente['nombre'], 
            cliente['direccion'], 
            cliente['telefono'], 
            cliente['fecha']
        ))
        idcliente = cursor.lastrowid # Recuperamos el ID que MySQL le asignó al cliente
        
        # Insertar las pizzas asociadas a ese cliente
        sql_pedido = """
            INSERT INTO pedido (idcliente, tamano, ingredientes, numero_pizzas) 
            VALUES (%s, %s, %s, %s)
        """
        for pizza in pizzas:
            cursor.execute(sql_pedido, (
                idcliente, 
                pizza['tamano'], 
                pizza['ingredientes'], 
                pizza['numPizzas']
            ))
            
        conexion.commit() # Confirmar los cambios en la BD
        return jsonify({'mensaje': 'Pedido registrado correctamente'}), 201
        
    except Exception as e:
        conexion.rollback() # Si hay error, deshacemos los cambios
        print(f"\n❌ ERROR DE MYSQL: {str(e)}\n")
        return jsonify({'error': str(e)}), 500
        
    finally:
        cursor.close()
        conexion.close()

# ENDPOINT 2: Consultar ventas por día o mes
@app.route('/api/ventas', methods=['GET'])
def consultar_ventas():
    criterio = request.args.get('criterio')
    valor = request.args.get('valor', '').strip().lower()
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    # Traemos todos los clientes junto con sus pizzas
    sql = """
        SELECT c.idcliente, c.nombre_completo, c.fecha_pedido, 
               p.tamano, p.ingredientes, p.numero_pizzas 
        FROM clientes c 
        JOIN pedido p ON c.idcliente = p.idcliente
    """
    cursor.execute(sql)
    resultados = cursor.fetchall()
    
    cursor.close()
    conexion.close()
    
    ventas_agrupadas = {}
    dias_semana = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
    meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    
    for fila in resultados:
        fecha = fila['fecha_pedido'] # Formato Date
        
        # Filtrar si coincide con el día o el mes solicitado
        coincide = False
        if criterio == 'dia' and dias_semana[fecha.weekday()] == valor:
            coincide = True
        elif criterio == 'mes' and meses[fecha.month - 1] == valor:
            coincide = True
            
        if coincide:
            # Calcular subtotal dinámicamente
            precio_tamano = 40 if fila['tamano'] == 'Chica' else (80 if fila['tamano'] == 'Mediana' else 120)
            precio_ingredientes = 0
            ingredientes_str = fila['ingredientes'].lower()
            
            if 'jamón' in ingredientes_str or 'jamon' in ingredientes_str: precio_ingredientes += 10
            if 'piña' in ingredientes_str or 'pina' in ingredientes_str: precio_ingredientes += 10
            if 'champiñones' in ingredientes_str or 'champinones' in ingredientes_str: precio_ingredientes += 10
            
            subtotal = (precio_tamano + precio_ingredientes) * fila['numero_pizzas']
            
            # Sumar al total del cliente
            if fila['idcliente'] not in ventas_agrupadas:
                ventas_agrupadas[fila['idcliente']] = {
                    'cliente_nombre': fila['nombre_completo'],
                    'total': 0
                }
            ventas_agrupadas[fila['idcliente']]['total'] += subtotal
            
    return jsonify(list(ventas_agrupadas.values()))

# Iniciar el servidor
if __name__ == '__main__':
    app.run(debug=True, port=5000)