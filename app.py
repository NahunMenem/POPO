from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import pytz
from flask_migrate import Migrate
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from sqlalchemy import func

load_dotenv()  # Carga las variables de entorno desde el archivo .env

app = Flask(__name__)

app.secret_key = os.urandom(24)  # Genera una clave secreta aleatoria

# Configuración de la base de datos PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modelo para la tabla 'usuarios'
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')

# Modelo para la tabla 'equipos'
class Equipo(db.Model):
    __tablename__ = 'equipos'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tipo_reparacion = db.Column(db.String(120), nullable=False)
    marca = db.Column(db.String(120), nullable=False)
    modelo = db.Column(db.String(120), nullable=False)
    tecnico = db.Column(db.String(120), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    nombre_cliente = db.Column(db.String(120), nullable=False)
    telefono = db.Column(db.String(20), nullable=False)
    nro_orden = db.Column(db.String(50), nullable=False)
    fecha = db.Column(db.String(20), nullable=False)
    hora = db.Column(db.String(20), nullable=False)

# Modelo para la tabla 'productos'
class Producto(db.Model):
    __tablename__ = 'productos'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(120), nullable=False)
    codigo_barras = db.Column(db.String(50), unique=True, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    precio = db.Column(db.Float, nullable=False)
    precio_costo = db.Column(db.Float, nullable=False)

# Modelo para la tabla 'ventas'
class Venta(db.Model):
    __tablename__ = 'ventas'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.String(20), nullable=False)
    nombre_manual = db.Column(db.String(120))
    precio_manual = db.Column(db.Float)
    tipo_pago = db.Column(db.String(50), nullable=False)
    dni_cliente = db.Column(db.String(20), nullable=False)

# Modelo para la tabla 'reparaciones'
class Reparacion(db.Model):
    __tablename__ = 'reparaciones'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_servicio = db.Column(db.String(120), nullable=False)
    precio = db.Column(db.Float, nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    tipo_pago = db.Column(db.String(50), nullable=False)
    dni_cliente = db.Column(db.String(20), nullable=False)
    fecha = db.Column(db.String(20), nullable=False)

# Modelo para la tabla 'egresos'
class Egreso(db.Model):
    __tablename__ = 'egresos'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fecha = db.Column(db.String(20), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    descripcion = db.Column(db.String(200), nullable=False)
    tipo_pago = db.Column(db.String(50), nullable=False)

# Modelo para la tabla 'mercaderia_fallada'
class MercaderiaFallada(db.Model):
    __tablename__ = 'mercaderia_fallada'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.String(20), nullable=False)
    descripcion = db.Column(db.String(200), nullable=False)

# Crear todas las tablas en la base de datos
# Crea las tablas dentro del contexto de la aplicación
with app.app_context():
    db.create_all()

# Proteger rutas que requieren autenticación
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Ruta principal (redirige al login si no está autenticado)
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('inicio'))  # Redirige a la página principal del sistema
    return redirect(url_for('login'))  # Redirige al login si no está autenticado



# Ruta para el login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('inicio'))  # Redirige a la página principal si ya está autenticado

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Consultar el usuario en la base de datos
        user = Usuario.query.filter_by(username=username).first()

        if user and user.password == password:
            session['username'] = user.username
            session['role'] = user.role
            flash('Login exitoso!', 'success')
            return redirect(url_for('inicio'))  # Redirige a la página principal después del login
        else:
            flash('Usuario o contraseña incorrectos', 'error')

    return render_template('login.html')

# Ruta para la página principal del sistema (después del login)
@app.route('/inicio')
def inicio():
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirige al login si no está autenticado
    return render_template('inicio.html')

# Ruta para el logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    flash('Has cerrado sesión correctamente.', 'success')
    return redirect(url_for('login'))

# Ruta para registrar ventas
@app.route('/registrar_venta', methods=['GET', 'POST'])
def registrar_venta():
    if 'carrito' not in session:
        session['carrito'] = []

    if request.method == 'POST':
        if 'buscar' in request.form:
            busqueda = request.form['busqueda']
            productos = Producto.query.filter(
                (Producto.codigo_barras == busqueda) | (Producto.nombre.like(f'%{busqueda}%'))
            ).all()
            return render_template('registrar_venta.html', productos=productos, carrito=session['carrito'])

        elif 'agregar' in request.form:
            producto_id = request.form['producto_id']
            cantidad = int(request.form['cantidad'])

            producto = Producto.query.get(producto_id)
            if producto:
                if producto.precio is not None:
                    item = {
                        'id': producto.id,
                        'nombre': producto.nombre,
                        'precio': producto.precio,
                        'cantidad': cantidad
                    }
                    session['carrito'].append(item)
                    session.modified = True
                else:
                    return f"Error: El producto '{producto.nombre}' no tiene un precio definido."
            else:
                return "Error: Producto no encontrado."

        elif 'agregar_manual' in request.form:
            nombre = request.form['nombre_manual']
            precio = float(request.form['precio_manual'])
            cantidad = int(request.form['cantidad_manual'])

            item = {
                'id': None,
                'nombre': nombre,
                'precio': precio,
                'cantidad': cantidad
            }
            session['carrito'].append(item)
            session.modified = True

        elif 'registrar' in request.form:
            if not session['carrito']:
                return "El carrito está vacío. Agrega productos antes de registrar la venta."

            tipo_pago = request.form['tipo_pago']
            dni_cliente = request.form['dni_cliente']
            argentina_tz = pytz.timezone('America/Argentina/Buenos_Aires')
            fecha_actual = datetime.now(argentina_tz).strftime('%Y-%m-%d %H:%M:%S')

            for item in session['carrito']:
                producto_id = item['id']
                nombre = item['nombre']
                precio = item['precio']
                cantidad = item['cantidad']

                if producto_id is not None:
                    producto = Producto.query.get(producto_id)
                    if producto and producto.stock >= cantidad:
                        nueva_venta = Venta(
                            producto_id=producto_id,
                            cantidad=cantidad,
                            fecha=fecha_actual,
                            nombre_manual=None,
                            precio_manual=None,
                            tipo_pago=tipo_pago,
                            dni_cliente=dni_cliente
                        )
                        db.session.add(nueva_venta)
                        producto.stock -= cantidad
                    else:
                        return f"No hay suficiente stock para el producto: {nombre}"
                else:
                    nueva_reparacion = Reparacion(
                        nombre_servicio=nombre,
                        precio=precio,
                        cantidad=cantidad,
                        tipo_pago=tipo_pago,
                        dni_cliente=dni_cliente,
                        fecha=fecha_actual
                    )
                    db.session.add(nueva_reparacion)

            db.session.commit()
            session.pop('carrito', None)
            return redirect(url_for('index'))

        elif 'vaciar' in request.form:
            session.pop('carrito', None)
            return redirect(url_for('registrar_venta'))

    total = sum(item['precio'] * item['cantidad'] for item in session['carrito'])
    return render_template('registrar_venta.html', productos=None, carrito=session['carrito'], total=total)

# Ruta para mostrar los productos más vendidos
@app.route('/productos_mas_vendidos')
def productos_mas_vendidos():
    productos = Producto.query.order_by(Producto.cantidad_vendida.desc()).limit(5).all()
    total_ventas = db.session.query(db.func.sum(Producto.cantidad_vendida)).scalar() or 0

    productos_con_porcentaje = []
    for producto in productos:
        porcentaje = (producto.cantidad_vendida / total_ventas) * 100 if total_ventas > 0 else 0
        productos_con_porcentaje.append({
            'nombre': producto.nombre,
            'precio': producto.precio,
            'cantidad_vendida': producto.cantidad_vendida,
            'porcentaje': round(porcentaje, 2)
        })

    return render_template('productos_mas_vendidos.html', productos=productos_con_porcentaje, total_ventas=total_ventas)

# Ruta para productos por agotarse
@app.route('/productos_por_agotarse')
def productos_por_agotarse():
    productos = Producto.query.filter(Producto.stock <= 2).order_by(Producto.stock.asc()).all()
    return render_template('productos_por_agotarse.html', productos=productos)

# Ruta para ver las últimas 10 ventas del día
@app.route('/ultimas_ventas')
def ultimas_ventas():
    argentina_tz = pytz.timezone('America/Argentina/Buenos_Aires')
    fecha_actual = datetime.now(argentina_tz).strftime('%Y-%m-%d')

    ventas = db.session.query(
        Venta.id.label('venta_id'),
        Producto.nombre.label('nombre_producto'),
        Venta.cantidad,
        Producto.precio.label('precio_unitario'),
        (Venta.cantidad * Producto.precio).label('total'),
        Venta.fecha,
        Venta.tipo_pago
    ).join(Producto).filter(db.func.date(Venta.fecha) == fecha_actual).order_by(Venta.fecha.desc()).all()

    reparaciones = Reparacion.query.filter(db.func.date(Reparacion.fecha) == fecha_actual).order_by(Reparacion.fecha.desc()).all()

    total_ventas_por_pago = {}
    for venta in ventas:
        tipo_pago = venta.tipo_pago
        total = venta.total
        total_ventas_por_pago[tipo_pago] = total_ventas_por_pago.get(tipo_pago, 0) + total

    total_reparaciones_por_pago = {}
    for reparacion in reparaciones:
        tipo_pago = reparacion.tipo_pago
        total = reparacion.precio * reparacion.cantidad
        total_reparaciones_por_pago[tipo_pago] = total_reparaciones_por_pago.get(tipo_pago, 0) + total

    return render_template(
        'ultimas_ventas.html',
        ventas=ventas,
        reparaciones=reparaciones,
        fecha_actual=fecha_actual,
        total_ventas_por_pago=total_ventas_por_pago,
        total_reparaciones_por_pago=total_reparaciones_por_pago
    )

# Ruta para egresos
@app.route('/egresos', methods=['GET', 'POST'])
def egresos():
    if request.method == 'POST' and 'agregar' in request.form:
        fecha = request.form['fecha']
        monto = float(request.form['monto'])
        descripcion = request.form['descripcion']
        tipo_pago = request.form['tipo_pago']

        nuevo_egreso = Egreso(fecha=fecha, monto=monto, descripcion=descripcion, tipo_pago=tipo_pago)
        db.session.add(nuevo_egreso)
        db.session.commit()
        return redirect(url_for('egresos'))

    if request.method == 'POST' and 'eliminar' in request.form:
        egreso_id = request.form['egreso_id']
        egreso = Egreso.query.get(egreso_id)
        db.session.delete(egreso)
        db.session.commit()
        return redirect(url_for('egresos'))

    egresos = Egreso.query.order_by(Egreso.fecha.desc()).all()
    return render_template('egresos.html', egresos=egresos)

# Ruta para el dashboard
@app.route('/dashboard')
def dashboard():
    fecha_seleccionada = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))

    total_ventas_productos_dia = db.session.query(
        db.func.sum(Venta.cantidad * Producto.precio)
    ).join(Producto).filter(db.func.date(Venta.fecha) == fecha_seleccionada).scalar() or 0

    total_ventas_reparaciones_dia = db.session.query(
        db.func.sum(Reparacion.precio * Reparacion.cantidad)
    ).filter(db.func.date(Reparacion.fecha) == fecha_seleccionada).scalar() or 0

    total_ventas_dia = total_ventas_productos_dia + total_ventas_reparaciones_dia

    total_egresos_dia = db.session.query(
        db.func.sum(Egreso.monto)
    ).filter(db.func.date(Egreso.fecha) == fecha_seleccionada).scalar() or 0

    total_costo_dia = db.session.query(
        db.func.sum(Venta.cantidad * Producto.precio_costo)
    ).join(Producto).filter(db.func.date(Venta.fecha) == fecha_seleccionada).scalar() or 0

    ganancia_dia = total_ventas_dia - total_egresos_dia - total_costo_dia

    hoy = datetime.now()
    inicio_semana = (hoy - timedelta(days=hoy.weekday())).strftime('%Y-%m-%d')
    fin_semana = (hoy + timedelta(days=(6 - hoy.weekday()))).strftime('%Y-%m-%d')

    total_ventas_productos = db.session.query(
        db.func.sum(Venta.cantidad * Producto.precio)
    ).join(Producto).filter(db.func.date(Venta.fecha).between(inicio_semana, fin_semana)).scalar() or 0

    total_ventas_reparaciones = db.session.query(
        db.func.sum(Reparacion.precio * Reparacion.cantidad)
    ).filter(db.func.date(Reparacion.fecha).between(inicio_semana, fin_semana)).scalar() or 0

    total_ventas = total_ventas_productos + total_ventas_reparaciones

    total_egresos = db.session.query(
        db.func.sum(Egreso.monto)
    ).filter(db.func.date(Egreso.fecha).between(inicio_semana, fin_semana)).scalar() or 0

    total_costo = db.session.query(
        db.func.sum(Venta.cantidad * Producto.precio_costo)
    ).join(Producto).filter(db.func.date(Venta.fecha).between(inicio_semana, fin_semana)).scalar() or 0

    ganancia_semana = total_ventas - total_egresos - total_costo

    return render_template('dashboard.html',
                          total_ventas=total_ventas,
                          total_egresos=total_egresos,
                          total_costo=total_costo,
                          ganancia_semana=ganancia_semana,
                          inicio_semana=inicio_semana,
                          fin_semana=fin_semana,
                          total_ventas_dia=total_ventas_dia,
                          total_egresos_dia=total_egresos_dia,
                          total_costo_dia=total_costo_dia,
                          ganancia_dia=ganancia_dia,
                          fecha_seleccionada=fecha_seleccionada)

# Ruta para la caja
@app.route('/caja')
def caja():
    argentina_tz = pytz.timezone('America/Argentina/Buenos_Aires')
    fecha_actual = datetime.now(argentina_tz).strftime('%Y-%m-%d')

    ventas = db.session.query(
        Venta.id.label('venta_id'),
        Producto.nombre.label('nombre_producto'),
        Venta.cantidad,
        Producto.precio.label('precio_unitario'),
        (Venta.cantidad * Producto.precio).label('total'),
        Venta.fecha,
        Venta.tipo_pago
    ).join(Producto).filter(db.func.date(Venta.fecha) == fecha_actual).order_by(Venta.fecha.desc()).all()

    reparaciones = Reparacion.query.filter(db.func.date(Reparacion.fecha) == fecha_actual).order_by(Reparacion.fecha.desc()).all()

    egresos = Egreso.query.filter(db.func.date(Egreso.fecha) == fecha_actual).order_by(Egreso.fecha.desc()).all()

    total_ventas_por_pago = {}
    for venta in ventas:
        tipo_pago = venta.tipo_pago
        total = venta.total
        total_ventas_por_pago[tipo_pago] = total_ventas_por_pago.get(tipo_pago, 0) + total

    total_reparaciones_por_pago = {}
    for reparacion in reparaciones:
        tipo_pago = reparacion.tipo_pago
        total = reparacion.precio * reparacion.cantidad
        total_reparaciones_por_pago[tipo_pago] = total_reparaciones_por_pago.get(tipo_pago, 0) + total

    total_combinado_por_pago = {}
    for tipo_pago, total in total_ventas_por_pago.items():
        total_combinado_por_pago[tipo_pago] = total_combinado_por_pago.get(tipo_pago, 0) + total
    for tipo_pago, total in total_reparaciones_por_pago.items():
        total_combinado_por_pago[tipo_pago] = total_combinado_por_pago.get(tipo_pago, 0) + total

    total_egresos_por_pago = {}
    for egreso in egresos:
        tipo_pago = egreso.tipo_pago
        monto = egreso.monto
        if tipo_pago in total_egresos_por_pago:
            total_egresos_por_pago[tipo_pago] += monto
        else:
            total_egresos_por_pago[tipo_pago] = monto

    neto_por_pago = {}
    for tipo_pago, total in total_combinado_por_pago.items():
        egresos_tipo_pago = total_egresos_por_pago.get(tipo_pago, 0)
        neto_por_pago[tipo_pago] = total - egresos_tipo_pago

    return render_template(
        'caja.html',
        fecha_actual=fecha_actual,
        total_ventas_por_pago=total_ventas_por_pago,
        total_reparaciones_por_pago=total_reparaciones_por_pago,
        total_combinado_por_pago=total_combinado_por_pago,
        total_egresos_por_pago=total_egresos_por_pago,
        neto_por_pago=neto_por_pago
    )

# Ruta para reparaciones
@app.route('/reparaciones', methods=['GET', 'POST'])
def reparaciones():
    if request.method == 'POST':
        tipo_reparacion = request.form['tipo_reparacion']
        marca = request.form['equipo']
        modelo = request.form['modelo']
        tecnico = request.form['tecnico']
        monto = float(request.form['monto'])
        nombre_cliente = request.form['nombre_cliente']
        telefono = request.form['telefono']
        nro_orden = request.form['nro_orden']
        fecha = datetime.now().strftime('%Y-%m-%d')
        hora = datetime.now().strftime('%H:%M:%S')

        nuevo_equipo = Equipo(
            tipo_reparacion=tipo_reparacion,
            marca=marca,
            modelo=modelo,
            tecnico=tecnico,
            monto=monto,
            nombre_cliente=nombre_cliente,
            telefono=telefono,
            nro_orden=nro_orden,
            fecha=fecha,
            hora=hora
        )
        db.session.add(nuevo_equipo)
        db.session.commit()

    fecha_inicio = datetime.now() - timedelta(days=7)
    ultimos_equipos = Equipo.query.filter(Equipo.fecha >= fecha_inicio.strftime('%Y-%m-%d')).all()

    datos_tecnicos = db.session.query(
        Equipo.tecnico,
        db.func.count(Equipo.id).label('cantidad')
    ).group_by(Equipo.tecnico).all()

    equipos_por_tecnico = {row.tecnico: row.cantidad for row in datos_tecnicos}

    return render_template(
        'reparaciones.html',
        ultimos_equipos=ultimos_equipos,
        equipos_por_tecnico=equipos_por_tecnico
    )

# Ruta para eliminar reparaciones
@app.route('/eliminar_reparacion/<int:id>', methods=['POST'])
def eliminar_reparacion(id):
    equipo = Equipo.query.get(id)
    db.session.delete(equipo)
    db.session.commit()
    return redirect(url_for('reparaciones'))

# Ruta para actualizar estado de reparaciones
@app.route('/actualizar_estado', methods=['POST'])
def actualizar_estado():
    data = request.get_json()
    nro_orden = data['nro_orden']
    estado = data['estado']

    equipo = Equipo.query.filter_by(nro_orden=nro_orden).first()
    if equipo:
        equipo.estado = estado
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False})

# Ruta para mercadería fallada
@app.route('/mercaderia_fallada', methods=['GET', 'POST'])
def mercaderia_fallada():
    if request.method == 'POST' and 'buscar' in request.form:
        busqueda = request.form['busqueda']
        productos = Producto.query.filter(
            (Producto.nombre.like(f'%{busqueda}%')) | (Producto.codigo_barras.like(f'%{busqueda}%'))
        ).all()
        return render_template('mercaderia_fallada.html', productos=productos)

    if request.method == 'POST' and 'registrar_fallada' in request.form:
        producto_id = request.form['producto_id']
        cantidad = int(request.form['cantidad'])
        descripcion = request.form['descripcion']
        fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        producto = Producto.query.get(producto_id)
        if producto and producto.stock >= cantidad:
            nueva_fallada = MercaderiaFallada(
                producto_id=producto_id,
                cantidad=cantidad,
                fecha=fecha,
                descripcion=descripcion
            )
            db.session.add(nueva_fallada)
            producto.stock -= cantidad
            db.session.commit()
            return redirect(url_for('mercaderia_fallada'))
        else:
            return f"No hay suficiente stock para el producto seleccionado."

    historial = db.session.query(
        MercaderiaFallada.id,
        Producto.nombre,
        MercaderiaFallada.cantidad,
        MercaderiaFallada.fecha,
        MercaderiaFallada.descripcion
    ).join(Producto).order_by(MercaderiaFallada.fecha.desc()).all()

    return render_template('mercaderia_fallada.html', historial=historial)





# Ruta para agregar stock
@app.route('/agregar_stock', methods=['GET', 'POST'])
def agregar_stock():
    busqueda = request.args.get('busqueda', '')

    try:
        if request.method == 'POST' and 'eliminar' in request.form:
            producto_id = request.form['producto_id']
            producto = Producto.query.get(producto_id)
            db.session.delete(producto)
            db.session.commit()
            return redirect(url_for('agregar_stock'))

        if request.method == 'POST' and 'editar' in request.form:
            producto_id = request.form['producto_id']
            nombre = request.form['nombre']
            codigo_barras = request.form['codigo_barras']
            stock = int(request.form['stock'])
            precio = float(request.form['precio'])
            precio_costo = float(request.form['precio_costo'])

            producto = Producto.query.get(producto_id)
            producto.nombre = nombre
            producto.codigo_barras = codigo_barras
            producto.stock = stock
            producto.precio = precio
            producto.precio_costo = precio_costo
            db.session.commit()
            return redirect(url_for('agregar_stock'))

        if request.method == 'POST' and 'agregar_stock' in request.form:
            producto_id = request.form['producto_id']
            cantidad = int(request.form['cantidad'])

            producto = Producto.query.get(producto_id)
            producto.stock += cantidad
            db.session.commit()
            return redirect(url_for('agregar_stock'))

        if request.method == 'POST' and 'agregar' in request.form:
            nombre = request.form['nombre']
            codigo_barras = request.form['codigo_barras']
            stock = int(request.form['stock'])
            precio = float(request.form['precio'])
            precio_costo = float(request.form['precio_costo'])

            nuevo_producto = Producto(
                nombre=nombre,
                codigo_barras=codigo_barras,
                stock=stock,
                precio=precio,
                precio_costo=precio_costo
            )
            db.session.add(nuevo_producto)
            db.session.commit()
            return redirect(url_for('agregar_stock'))

        if busqueda:
            productos = Producto.query.filter(
                (Producto.nombre.like(f'%{busqueda}%')) | (Producto.codigo_barras.like(f'%{busqueda}%'))
            ).all()
        else:
            productos = Producto.query.all()

    except Exception as e:
        db.session.rollback()
        return f"Error: {str(e)}"

    return render_template('agregar_stock.html', productos=productos, busqueda=busqueda)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
