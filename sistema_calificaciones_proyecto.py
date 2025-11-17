#Sistema de Gestión de Calificaciones con Lógica Formal
#Hecho por: María José Herrera Bonilla

import sqlite3
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

class EstadoApelacion(Enum):

    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"

class ReglasLogicas:
     
    @staticmethod
    def validar_nota(nota: float) -> bool:
        return 0.0 <= nota <= 5.0
    
    @staticmethod
    def validar_porcentaje(porcentaje: float) -> bool:
        return 0 <= porcentaje <= 100
    
    @staticmethod
    def validar_justificacion(texto: str) -> bool:
        return len(texto.strip()) >= 20
    
    @staticmethod
    def validar_apelacion(texto: str) -> bool:
        return len(texto.strip()) >= 20
    
    @staticmethod
    def dentro_plazo_apelacion(fecha_nota: datetime, fecha_actual: datetime, dias_limite: int = 3) -> bool:
        diferencia = fecha_actual - fecha_nota
        return diferencia.days <= dias_limite
    
    @staticmethod
    def puede_modificar_nota(rol: str, es_propietario: bool) -> bool:
        return rol == "profesor" and es_propietario
    
    @staticmethod
    def suma_porcentajes_correcta(porcentajes: List[float]) -> bool:
        return abs(sum(porcentajes) - 100.0) < 0.01
    
    @staticmethod
    def inferir_necesidad_nota(nota_actual: float, nota_objetivo: float, 
                               porcentaje_restante: float, porcentaje_faltante: float) -> float:
        if porcentaje_faltante == 0:
            return 0.0
        puntos_actuales = nota_actual * (porcentaje_restante / 100)
        puntos_necesarios = nota_objetivo - puntos_actuales
        nota_necesaria = (puntos_necesarios * 100) / porcentaje_faltante
        return max(0.0, min(5.0, nota_necesaria))

@dataclass
class Usuario:
    id: int
    username: str
    password: str
    rol: str
    nombre_completo: str

@dataclass
class Nota:
    id: Optional[int]
    estudiante_id: int
    asignatura_id: int
    corte: int
    actividad: str
    nota: float
    porcentaje: float
    fecha_registro: datetime
    profesor_id: int
    justificacion: str


@dataclass
class Apelacion:
    id: Optional[int]
    nota_id: int
    estudiante_id: int
    descripcion: str
    estado: EstadoApelacion
    fecha_creacion: datetime
    respuesta_profesor: Optional[str]
    fecha_respuesta: Optional[datetime]


class BaseDatos:
   
    def __init__(self, db_name: str = "calificaciones.db"):
        self.db_name = db_name
        self.inicializar_db()
    
    def obtener_conexion(self):
        return sqlite3.connect(self.db_name)
    
    def inicializar_db(self):
       #crea tablas si no existen
        conn = self.obtener_conexion()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                rol TEXT NOT NULL,
                nombre_completo TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS asignaturas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                nombre TEXT NOT NULL,
                creditos INTEGER NOT NULL,
                profesor_id INTEGER,
                FOREIGN KEY (profesor_id) REFERENCES usuarios(id)
            )
        ''')
    
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inscripciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                estudiante_id INTEGER NOT NULL,
                asignatura_id INTEGER NOT NULL,
                periodo TEXT NOT NULL,
                FOREIGN KEY (estudiante_id) REFERENCES usuarios(id),
                FOREIGN KEY (asignatura_id) REFERENCES asignaturas(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                estudiante_id INTEGER NOT NULL,
                asignatura_id INTEGER NOT NULL,
                corte INTEGER NOT NULL,
                actividad TEXT NOT NULL,
                nota REAL NOT NULL,
                porcentaje REAL NOT NULL,
                fecha_registro TEXT NOT NULL,
                profesor_id INTEGER NOT NULL,
                justificacion TEXT NOT NULL,
                FOREIGN KEY (estudiante_id) REFERENCES usuarios(id),
                FOREIGN KEY (asignatura_id) REFERENCES asignaturas(id),
                FOREIGN KEY (profesor_id) REFERENCES usuarios(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS apelaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nota_id INTEGER NOT NULL,
                estudiante_id INTEGER NOT NULL,
                descripcion TEXT NOT NULL,
                estado TEXT NOT NULL,
                fecha_creacion TEXT NOT NULL,
                respuesta_profesor TEXT,
                fecha_respuesta TEXT,
                FOREIGN KEY (nota_id) REFERENCES notas(id),
                FOREIGN KEY (estudiante_id) REFERENCES usuarios(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historial_modificaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nota_id INTEGER NOT NULL,
                nota_anterior REAL NOT NULL,
                nota_nueva REAL NOT NULL,
                fecha_modificacion TEXT NOT NULL,
                profesor_id INTEGER NOT NULL,
                justificacion TEXT NOT NULL,
                FOREIGN KEY (nota_id) REFERENCES notas(id),
                FOREIGN KEY (profesor_id) REFERENCES usuarios(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        self._insertar_datos_prueba()
    
    def _insertar_datos_prueba(self):
    
        conn = self.obtener_conexion()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        if cursor.fetchone()[0] == 0:
            #usuarios de prueba
            usuarios = [
                ("profesor1", "pass123", "profesor", "Dr. Juan Pérez"),
                ("profesor2", "pass123", "profesor", "Dra. María García"),
                ("estudiante1", "pass123", "estudiante", "Carlos Rodríguez"),
                ("estudiante2", "pass123", "estudiante", "Ana Martínez"),
            ]
            cursor.executemany(
                "INSERT INTO usuarios (username, password, rol, nombre_completo) VALUES (?, ?, ?, ?)",
                usuarios
            )
            
            #materias/asignaturas de prueba
            asignaturas = [
                ("MAT101", "Cálculo Diferencial", 4, 1),
                ("FIS101", "Física Mecánica", 4, 2),
                ("PROG101", "Programación I", 3, 1),
            ]
            cursor.executemany(
                "INSERT INTO asignaturas (codigo, nombre, creditos, profesor_id) VALUES (?, ?, ?, ?)",
                asignaturas
            )
            
            # inscribir estudiantes
            inscripciones = [
                (3, 1, "2025-1"),
                (3, 2, "2025-1"),
                (4, 1, "2025-1"),
                (4, 3, "2025-1"),
            ]
            cursor.executemany(
                "INSERT INTO inscripciones (estudiante_id, asignatura_id, periodo) VALUES (?, ?, ?)",
                inscripciones
            )
            
            conn.commit()
        
        conn.close()

    def autenticar_usuario(self, username: str, password: str) -> Optional[Usuario]:
        conn = self.obtener_conexion()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, password, rol, nombre_completo FROM usuarios WHERE username = ? AND password = ?",
            (username, password)
        )
        resultado = cursor.fetchone()
        conn.close()
        
        if resultado:
            return Usuario(*resultado)
        return None
    
    def registrar_nota(self, nota: Nota) -> int:
        #registra una nueva nota
        conn = self.obtener_conexion()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO notas (estudiante_id, asignatura_id, corte, actividad, nota, 
                              porcentaje, fecha_registro, profesor_id, justificacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (nota.estudiante_id, nota.asignatura_id, nota.corte, nota.actividad,
              nota.nota, nota.porcentaje, nota.fecha_registro.isoformat(),
              nota.profesor_id, nota.justificacion))
        nota_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return nota_id
    
    def modificar_nota(self, nota_id: int, nueva_nota: float, justificacion: str, profesor_id: int):
       #modifica una nota existente y registra el cambio en el historial 
        conn = self.obtener_conexion()
        cursor = conn.cursor()
        
        #obtener nota anterior
        cursor.execute("SELECT nota FROM notas WHERE id = ?", (nota_id,))
        nota_anterior = cursor.fetchone()[0]
        
        #actualizar nota
        cursor.execute(
            "UPDATE notas SET nota = ?, justificacion = ? WHERE id = ?",
            (nueva_nota, justificacion, nota_id)
        )
        
        #registrar en historial
        cursor.execute('''
            INSERT INTO historial_modificaciones 
            (nota_id, nota_anterior, nota_nueva, fecha_modificacion, profesor_id, justificacion)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (nota_id, nota_anterior, nueva_nota, datetime.now().isoformat(), 
              profesor_id, justificacion))
        
        conn.commit()
        conn.close()
    
    def obtener_notas_estudiante(self, estudiante_id: int, asignatura_id: Optional[int] = None) -> List[Nota]:
        #notas del estudiante
        conn = self.obtener_conexion()
        cursor = conn.cursor()
        
        if asignatura_id:
            query = '''
                SELECT id, estudiante_id, asignatura_id, corte, actividad, nota, 
                       porcentaje, fecha_registro, profesor_id, justificacion
                FROM notas 
                WHERE estudiante_id = ? AND asignatura_id = ?
                ORDER BY corte, fecha_registro
            '''
            cursor.execute(query, (estudiante_id, asignatura_id))
        else:
            query = '''
                SELECT id, estudiante_id, asignatura_id, corte, actividad, nota, 
                       porcentaje, fecha_registro, profesor_id, justificacion
                FROM notas 
                WHERE estudiante_id = ?
                ORDER BY asignatura_id, corte, fecha_registro
            '''
            cursor.execute(query, (estudiante_id,))
        
        notas = []
        for row in cursor.fetchall():
            nota = Nota(
                id=row[0], estudiante_id=row[1], asignatura_id=row[2],
                corte=row[3], actividad=row[4], nota=row[5], porcentaje=row[6],
                fecha_registro=datetime.fromisoformat(row[7]),
                profesor_id=row[8], justificacion=row[9]
            )
            notas.append(nota)
        
        conn.close()
        return notas
    

    def crear_apelacion(self, apelacion: Apelacion) -> int:
        #crear apelacion
        conn = self.obtener_conexion()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO apelaciones (nota_id, estudiante_id, descripcion, estado, fecha_creacion)
            VALUES (?, ?, ?, ?, ?)
        ''', (apelacion.nota_id, apelacion.estudiante_id, apelacion.descripcion,
              apelacion.estado.value, apelacion.fecha_creacion.isoformat()))
        apelacion_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return apelacion_id
    
    def responder_apelacion(self, apelacion_id: int, respuesta: str, 
                           estado: EstadoApelacion):
        #responder apelacion
        conn = self.obtener_conexion()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE apelaciones 
            SET respuesta_profesor = ?, estado = ?, fecha_respuesta = ?
            WHERE id = ?
        ''', (respuesta, estado.value, datetime.now().isoformat(), apelacion_id))
        conn.commit()
        conn.close()
    
    def obtener_apelaciones_estudiante(self, estudiante_id: int) -> List[Apelacion]:
        #obtener las apelaciones de un estudiante
        conn = self.obtener_conexion()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, nota_id, estudiante_id, descripcion, estado, 
                   fecha_creacion, respuesta_profesor, fecha_respuesta
            FROM apelaciones WHERE estudiante_id = ?
            ORDER BY fecha_creacion DESC
        ''', (estudiante_id,))
        
        apelaciones = []
        for row in cursor.fetchall():
            apelacion = Apelacion(
                id=row[0], nota_id=row[1], estudiante_id=row[2],
                descripcion=row[3], estado=EstadoApelacion(row[4]),
                fecha_creacion=datetime.fromisoformat(row[5]),
                respuesta_profesor=row[6],
                fecha_respuesta=datetime.fromisoformat(row[7]) if row[7] else None
            )
            apelaciones.append(apelacion)
        
        conn.close()
        return apelaciones
    
    def obtener_apelaciones_profesor(self, profesor_id: int) -> List[Tuple]:
        #apelaciones pendientes para el profesor
        conn = self.obtener_conexion()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.id, a.nota_id, a.estudiante_id, a.descripcion, a.estado,
                   a.fecha_creacion, u.nombre_completo, n.actividad, n.nota
            FROM apelaciones a
            JOIN notas n ON a.nota_id = n.id
            JOIN usuarios u ON a.estudiante_id = u.id
            WHERE n.profesor_id = ?
            ORDER BY a.fecha_creacion DESC
        ''', (profesor_id,))
        
        resultados = cursor.fetchall()
        conn.close()
        return resultados
    
    def obtener_asignaturas_profesor(self, profesor_id: int) -> List[Tuple]:
        #asignaturas del profesor
        conn = self.obtener_conexion()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, codigo, nombre, creditos
            FROM asignaturas WHERE profesor_id = ?
        ''', (profesor_id,))
        resultados = cursor.fetchall()
        conn.close()
        return resultados
    
    def obtener_estudiantes_asignatura(self, asignatura_id: int) -> List[Tuple]:
        #estudiantes inscritos en la asignatura
        conn = self.obtener_conexion()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.id, u.nombre_completo, u.username
            FROM usuarios u
            JOIN inscripciones i ON u.id = i.estudiante_id
            WHERE i.asignatura_id = ? AND u.rol = 'estudiante'
        ''', (asignatura_id,))
        resultados = cursor.fetchall()
        conn.close()
        return resultados
    
    def obtener_asignaturas_estudiante(self, estudiante_id: int) -> List[Tuple]:
        #asignaturas inscritas del estudiante
        conn = self.obtener_conexion()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.id, a.codigo, a.nombre, a.creditos, u.nombre_completo
            FROM asignaturas a
            JOIN inscripciones i ON a.id = i.asignatura_id
            JOIN usuarios u ON a.profesor_id = u.id
            WHERE i.estudiante_id = ?
        ''', (estudiante_id,))
        resultados = cursor.fetchall()
        conn.close()
        return resultados
    
    def obtener_historial_modificaciones(self, nota_id: int) -> List[Tuple]:
        #historial de modificaciones de una nota
        conn = self.obtener_conexion()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT h.nota_anterior, h.nota_nueva, h.fecha_modificacion,
                   u.nombre_completo, h.justificacion
            FROM historial_modificaciones h
            JOIN usuarios u ON h.profesor_id = u.id
            WHERE h.nota_id = ?
            ORDER BY h.fecha_modificacion DESC
        ''', (nota_id,))
        resultados = cursor.fetchall()
        conn.close()
        return resultados

class ServicioCalificaciones:
    
    def __init__(self, db: BaseDatos):
        self.db = db
        self.logica = ReglasLogicas()
    
    def calcular_promedio_corte(self, estudiante_id: int, asignatura_id: int, corte: int) -> float:
        #promedio del corte
        notas = self.db.obtener_notas_estudiante(estudiante_id, asignatura_id)
        notas_corte = [n for n in notas if n.corte == corte]
        
        if not notas_corte:
            return 0.0
        
        suma_ponderada = sum(n.nota * (n.porcentaje / 100) for n in notas_corte)
        return round(suma_ponderada, 2)
    
    def calcular_promedio_final(self, estudiante_id: int, asignatura_id: int) -> float:
        #promedio final
        promedios = []
        for corte in [1, 2, 3]:
            promedio = self.calcular_promedio_corte(estudiante_id, asignatura_id, corte)
            promedios.append(promedio)
        
        if not promedios:
            return 0.0
        
        # porcentajes 1er corte y 2do corte = 30%, 3er corte = 40%
        pesos = {1: 0.3, 2: 0.3, 3: 0.4}
        promedio_ponderado = (
            promedios[0] * pesos[1] +
            promedios[1] * pesos[2] +
            promedios[2] * pesos[3]
        )
        return round(promedio_ponderado, 2)
    
    def simular_nota_necesaria(self, estudiante_id: int, asignatura_id: int,
                              nota_objetivo: float) -> Dict:
        #simular nota necesaria para alcanzar x nota
        notas = self.db.obtener_notas_estudiante(estudiante_id, asignatura_id)
        
        #calcular promedio actual
        promedio_actual = self.calcular_promedio_final(estudiante_id, asignatura_id)
        
        #calcular porcentaje completado y faltante
        porcentaje_completado = sum(n.porcentaje for n in notas) / 3  # Dividido por 3 cortes
        porcentaje_faltante = 100 - porcentaje_completado
        
        #calcular nota necesaria por inferencia
        nota_necesaria = self.logica.inferir_necesidad_nota(
            promedio_actual, nota_objetivo, porcentaje_completado, porcentaje_faltante
        )
        
        return {
            "promedio_actual": promedio_actual,
            "nota_objetivo": nota_objetivo,
            "porcentaje_completado": porcentaje_completado,
            "porcentaje_faltante": porcentaje_faltante,
            "nota_necesaria": nota_necesaria,
            "es_alcanzable": 0.0 <= nota_necesaria <= 5.0
        }

class InterfazCLI:
    
    def __init__(self):
        self.db = BaseDatos()
        self.servicio = ServicioCalificaciones(self.db)
        self.logica = ReglasLogicas()
        self.usuario_actual: Optional[Usuario] = None
    
    def limpiar_pantalla(self):
        print("\n" * 50)
    
    def mostrar_encabezado(self, titulo: str):
        print("\n" + "=" * 70)
        print(f"  {titulo}")
        print("=" * 70 + "\n")
    
    def iniciar(self):
        self.limpiar_pantalla()
        print("╔════════════════════════════════════════════════════════════╗")
        print("║   SISTEMA DE GESTIÓN DE CALIFICACIONES CON LÓGICA FORMAL  ║")
        print("╚════════════════════════════════════════════════════════════╝")
        
        while True:
            if not self.usuario_actual:
                self.menu_login()
            else:
                if self.usuario_actual.rol == "profesor":
                    self.menu_profesor()
                else:
                    self.menu_estudiante()
    
    def menu_login(self):
        #menu iniciar sesion
        self.mostrar_encabezado("INICIO DE SESIÓN")
        print("Usuarios de prueba:")
        print("  Profesores: profesor1/pass123, profesor2/pass123")
        print("  Estudiantes: estudiante1/pass123, estudiante2/pass123\n")
        
        username = input("Usuario: ").strip()
        password = input("Contraseña: ").strip()
        
        usuario = self.db.autenticar_usuario(username, password)
        if usuario:
            self.usuario_actual = usuario
            print(f"\n✓ Bienvenido, {usuario.nombre_completo}!")
            input("\nPresione Enter para continuar...")
        else:
            print("\n✗ Credenciales incorrectas.")
            input("\nPresione Enter para continuar...")
    
    def menu_profesor(self):
        #menu profesor
        self.limpiar_pantalla()
        self.mostrar_encabezado(f"MENÚ PROFESOR - {self.usuario_actual.nombre_completo}")
        
        print("1. Registrar nueva nota")
        print("2. Modificar nota existente")
        print("3. Ver apelaciones pendientes")
        print("4. Responder apelaciones")
        print("5. Ver historial de modificaciones")
        print("6. Generar reportes")
        print("0. Cerrar sesión")
        
        opcion = input("\nSeleccione una opción: ").strip()
        
        if opcion == "1":
            self.registrar_nota()
        elif opcion == "2":
            self.modificar_nota()
        elif opcion == "3":
            self.ver_apelaciones_profesor()
        elif opcion == "4":
            self.responder_apelacion()
        elif opcion == "5":
            self.ver_historial_modificaciones()
        elif opcion == "6":
            self.generar_reportes_profesor()
        elif opcion == "0":
            self.usuario_actual = None
        else:
            print("\n✗ Opción inválida.")
            input("\nPresione Enter para continuar...")
    
    def menu_estudiante(self):
        #menu estudiante
        self.limpiar_pantalla()
        self.mostrar_encabezado(f"MENÚ ESTUDIANTE - {self.usuario_actual.nombre_completo}")
        
        print("1. Consultar mis calificaciones")
        print("2. Ver promedios por corte")
        print("3. Calcular promedio final")
        print("4. Simular escenarios de notas")
        print("5. Generar apelación")
        print("6. Ver mis apelaciones")
        print("0. Cerrar sesión")
        
        opcion = input("\nSeleccione una opción: ").strip()
        
        if opcion == "1":
            self.consultar_calificaciones()
        elif opcion == "2":
            self.ver_promedios_cortes()
        elif opcion == "3":
            self.calcular_promedio_final()
        elif opcion == "4":
            self.simular_notas()
        elif opcion == "5":
            self.crear_apelacion()
        elif opcion == "6":
            self.ver_mis_apelaciones()
        elif opcion == "0":
            self.usuario_actual = None
        else:
            print("\n✗ Opción inválida.")
            input("\nPresione Enter para continuar...")
    
    #metodos para profesores
    def registrar_nota(self):
        #registrar nueva nota
        self.mostrar_encabezado("REGISTRAR NUEVA NOTA")
        
        #seleccionar asignatura
        asignaturas = self.db.obtener_asignaturas_profesor(self.usuario_actual.id)
        if not asignaturas:
            print("No tiene asignaturas asignadas.")
            input("\nPresione Enter para continuar...")
            return
        
        print("Asignaturas:")
        for i, (id_asig, codigo, nombre, creditos) in enumerate(asignaturas, 1):
            print(f"{i}. {codigo} - {nombre}")
        
        try:
            idx = int(input("\nSeleccione asignatura: ")) - 1
            asignatura_id = asignaturas[idx][0]
        except:
            print("\n✗ Selección inválida.")
            input("\nPresione Enter para continuar...")
            return
        
        #seleccionar estudiante
        estudiantes = self.db.obtener_estudiantes_asignatura(asignatura_id)
        if not estudiantes:
            print("\nNo hay estudiantes inscritos.")
            input("\nPresione Enter para continuar...")
            return
        
        print("\nEstudiantes:")
        for i, (id_est, nombre, username) in enumerate(estudiantes, 1):
            print(f"{i}. {nombre} ({username})")
        
        try:
            idx = int(input("\nSeleccione estudiante: ")) - 1
            estudiante_id = estudiantes[idx][0]
        except:
            print("\n✗ Selección inválida.")
            input("\nPresione Enter para continuar...")
            return
        
        #ingresar nota
        try:
            corte = int(input("\nCorte (1, 2 o 3): "))
            if corte not in [1, 2, 3]:
                raise ValueError
            
            actividad = input("Nombre de la actividad: ").strip()
            nota_valor = float(input("Nota (0.0 - 5.0): "))
            porcentaje = float(input("Porcentaje (0 - 100): "))
            justificacion = input("Justificación (mín. 20 caracteres): ").strip()
            
            #validar usando logica formal
            if not self.logica.validar_porcentaje(porcentaje):
                print("\n✗ El porcentaje debe estar entre 0 y 100")
                input("\nPresione Enter para continuar...")
                return
            
            if not self.logica.validar_justificacion(justificacion):
                print("\n✗ La justificación debe tener al menos 20 caracteres")
                input("\nPresione Enter para continuar...")
                return
            
            #crear objeto nota
            nota = Nota(
                id=None,
                estudiante_id=estudiante_id,
                asignatura_id=asignatura_id,
                corte=corte,
                actividad=actividad,
                nota=nota_valor,
                porcentaje=porcentaje,
                fecha_registro=datetime.now(),
                profesor_id=self.usuario_actual.id,
                justificacion=justificacion
            )
            
            #registrar en base de datos
            nota_id = self.db.registrar_nota(nota)
            print(f"\n:D Nota registrada exitosamente (ID: {nota_id})")
            
        except ValueError:
            print("\n D: Valores inválidos ingresados.")
        
        input("\nPresione Enter para continuar...")
    
    def modificar_nota(self):
        #modificar nota existente
        self.mostrar_encabezado("MODIFICAR NOTA EXISTENTE")
        
        try:
            nota_id = int(input("ID de la nota a modificar: "))
            
            #verificar q la nota existe Y pertenece al profesor
            conn = self.db.obtener_conexion()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT nota, profesor_id, fecha_registro FROM notas WHERE id = ?",
                (nota_id,)
            )
            resultado = cursor.fetchone()
            conn.close()
            
            if not resultado:
                print("\n✗ Nota no encontrada.")
                input("\nPresione Enter para continuar...")
                return
            
            nota_actual, profesor_id, fecha_registro_str = resultado
            
            #validar permisos usando logica formal
            if not self.logica.puede_modificar_nota("profesor", profesor_id == self.usuario_actual.id):
                print("\n✗ No tiene permisos para modificar esta nota.")
                input("\nPresione Enter para continuar...")
                return
            
            print(f"\nNota actual: {nota_actual}")
            nueva_nota = float(input("Nueva nota (0.0 - 5.0): "))
            justificacion = input("Justificación de la modificación (mín. 20 caracteres): ").strip()
            
            #validar usando logica formal
            if not self.logica.validar_nota(nueva_nota):
                print("\n✗ La nota debe estar entre 0.0 y 5.0")
                input("\nPresione Enter para continuar...")
                return
            
            if not self.logica.validar_justificacion(justificacion):
                print("\n✗ La justificación debe tener al menos 20 caracteres")
                input("\nPresione Enter para continuar...")
                return
            
            #modificar nota
            self.db.modificar_nota(nota_id, nueva_nota, justificacion, self.usuario_actual.id)
            print(f"\n✓ Nota modificada exitosamente de {nota_actual} a {nueva_nota}")
            
        except ValueError:
            print("\n✗ Valores inválidos ingresados.")
        
        input("\nPresione Enter para continuar...")
    
    def ver_apelaciones_profesor(self):
        #apelaciones pendientes del profesor
        self.mostrar_encabezado("APELACIONES PENDIENTES")
        
        apelaciones = self.db.obtener_apelaciones_profesor(self.usuario_actual.id)
        
        if not apelaciones:
            print("No hay apelaciones.")
            input("\nPresione Enter para continuar...")
            return
        
        for apel in apelaciones:
            id_apel, nota_id, est_id, desc, estado, fecha, nombre_est, actividad, nota = apel
            print(f"\n{'─' * 70}")
            print(f"ID Apelación: {id_apel}")
            print(f"Estudiante: {nombre_est}")
            print(f"Actividad: {actividad} | Nota: {nota}")
            print(f"Estado: {estado}")
            print(f"Fecha: {fecha}")
            print(f"Descripción: {desc}")
        
        input("\n\nPresione Enter para continuar...")
    
    def responder_apelacion(self):
        #responder apelacion
        self.mostrar_encabezado("RESPONDER APELACIÓN")
        
        try:
            apelacion_id = int(input("ID de la apelación: "))
            
            print("\nOpciones:")
            print("1. Aprobar apelación")
            print("2. Rechazar apelación")
            opcion = input("\nSeleccione: ").strip()
            
            respuesta = input("Respuesta al estudiante (mín. 20 caracteres): ").strip()
            
            if not self.logica.validar_justificacion(respuesta):
                print("\n✗ La respuesta debe tener al menos 20 caracteres")
                input("\nPresione Enter para continuar...")
                return
            
            if opcion == "1":
                estado = EstadoApelacion.APROBADA
                print("\nSi aprueba la apelación, debe modificar la nota.")
                modificar = input("¿Desea modificar la nota ahora? (s/n): ").strip().lower()
                if modificar == 's':
                    # Aquí se podría implementar la modificación directa
                    pass
            elif opcion == "2":
                estado = EstadoApelacion.RECHAZADA
            else:
                print("\n✗ Opción inválida.")
                input("\nPresione Enter para continuar...")
                return
            
            self.db.responder_apelacion(apelacion_id, respuesta, estado)
            print(f"\n✓ Apelación {estado.value} exitosamente.")
            
        except ValueError:
            print("\n✗ ID inválido.")
        
        input("\nPresione Enter para continuar...")
    
    def ver_historial_modificaciones(self):
        #historial de modificaciones de una nota
        self.mostrar_encabezado("HISTORIAL DE MODIFICACIONES")
        
        try:
            nota_id = int(input("ID de la nota: "))
            
            historial = self.db.obtener_historial_modificaciones(nota_id)
            
            if not historial:
                print("\nNo hay modificaciones registradas para esta nota.")
                input("\nPresione Enter para continuar...")
                return
            
            print(f"\n{'─' * 70}")
            for mod in historial:
                nota_ant, nota_nueva, fecha, profesor, justif = mod
                print(f"\nFecha: {fecha}")
                print(f"Profesor: {profesor}")
                print(f"Cambio: {nota_ant} → {nota_nueva}")
                print(f"Justificación: {justif}")
                print(f"{'─' * 70}")
            
        except ValueError:
            print("\n✗ ID inválido.")
        
        input("\nPresione Enter para continuar...")
    
    def generar_reportes_profesor(self):
        #reportes para el profesor
        self.mostrar_encabezado("REPORTES")
        
        print("1. Reporte de apelaciones por estado")
        print("2. Reporte de modificaciones recientes")
        print("3. Reporte de promedios por asignatura")
        
        opcion = input("\nSeleccione tipo de reporte: ").strip()
        
        if opcion == "1":
            #reporte de apelaciones
            conn = self.db.obtener_conexion()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.estado, COUNT(*) 
                FROM apelaciones a
                JOIN notas n ON a.nota_id = n.id
                WHERE n.profesor_id = ?
                GROUP BY a.estado
            ''', (self.usuario_actual.id,))
            
            print("\n" + "─" * 40)
            print("REPORTE DE APELACIONES POR ESTADO")
            print("─" * 40)
            for estado, cantidad in cursor.fetchall():
                print(f"{estado.capitalize()}: {cantidad}")
            
            conn.close()
        
        elif opcion == "2":
            #modificaciones recientes (ultimos 30 dias)
            fecha_limite = (datetime.now() - timedelta(days=30)).isoformat()
            conn = self.db.obtener_conexion()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*)
                FROM historial_modificaciones
                WHERE profesor_id = ? AND fecha_modificacion >= ?
            ''', (self.usuario_actual.id, fecha_limite))
            
            cantidad = cursor.fetchone()[0]
            print(f"\nModificaciones en los últimos 30 días: {cantidad}")
            conn.close()
        
        input("\nPresione Enter para continuar...")
    
    #metodos para estudiantes
    def consultar_calificaciones(self):
        #consultar sus calificaciones
        self.mostrar_encabezado("MIS CALIFICACIONES")
        
        #seleccionar asignatura
        asignaturas = self.db.obtener_asignaturas_estudiante(self.usuario_actual.id)
        
        if not asignaturas:
            print("No está inscrito en ninguna asignatura.")
            input("\nPresione Enter para continuar...")
            return
        
        print("Asignaturas:")
        for i, (id_asig, codigo, nombre, creditos, profesor) in enumerate(asignaturas, 1):
            print(f"{i}. {codigo} - {nombre} (Prof. {profesor})")
        
        try:
            idx = int(input("\nSeleccione asignatura: ")) - 1
            asignatura_id = asignaturas[idx][0]
            asignatura_nombre = asignaturas[idx][2]
        except:
            print("\n✗ Selección inválida.")
            input("\nPresione Enter para continuar...")
            return
        
        #notas
        notas = self.db.obtener_notas_estudiante(self.usuario_actual.id, asignatura_id)
        
        if not notas:
            print(f"\nNo hay calificaciones registradas para {asignatura_nombre}.")
            input("\nPresione Enter para continuar...")
            return
        
        print(f"\n{'═' * 70}")
        print(f"CALIFICACIONES - {asignatura_nombre}")
        print(f"{'═' * 70}")
        
        for corte in [1, 2, 3]:
            notas_corte = [n for n in notas if n.corte == corte]
            if notas_corte:
                print(f"\n{'─' * 70}")
                print(f"CORTE {corte}")
                print(f"{'─' * 70}")
                for nota in notas_corte:
                    print(f"\nActividad: {nota.actividad}")
                    print(f"Nota: {nota.nota} | Porcentaje: {nota.porcentaje}%")
                    print(f"Fecha: {nota.fecha_registro.strftime('%Y-%m-%d')}")
                    print(f"Justificación: {nota.justificacion}")
                
                promedio = self.servicio.calcular_promedio_corte(
                    self.usuario_actual.id, asignatura_id, corte
                )
                print(f"\n→ Promedio Corte {corte}: {promedio}")
        
        promedio_final = self.servicio.calcular_promedio_final(
            self.usuario_actual.id, asignatura_id
        )
        print(f"\n{'═' * 70}")
        print(f"PROMEDIO FINAL: {promedio_final}")
        print(f"{'═' * 70}")
        
        input("\nPresione Enter para continuar...")
    
    def ver_promedios_cortes(self):
        #ver promedios por corte
        self.mostrar_encabezado("PROMEDIOS POR CORTE")
        
        asignaturas = self.db.obtener_asignaturas_estudiante(self.usuario_actual.id)
        
        if not asignaturas:
            print("No está inscrito en ninguna asignatura.")
            input("\nPresione Enter para continuar...")
            return
        
        print(f"{'Asignatura':<30} {'Corte 1':<10} {'Corte 2':<10} {'Corte 3':<10}")
        print("─" * 70)
        
        for id_asig, codigo, nombre, creditos, profesor in asignaturas:
            promedios = []
            for corte in [1, 2, 3]:
                prom = self.servicio.calcular_promedio_corte(
                    self.usuario_actual.id, id_asig, corte
                )
                promedios.append(f"{prom:.2f}" if prom > 0 else "---")
            
            print(f"{nombre:<30} {promedios[0]:<10} {promedios[1]:<10} {promedios[2]:<10}")
        
        input("\nPresione Enter para continuar...")
    
    def calcular_promedio_final(self):
        #promedio final de todas las asignaturas
        self.mostrar_encabezado("PROMEDIOS FINALES")
        
        asignaturas = self.db.obtener_asignaturas_estudiante(self.usuario_actual.id)
        
        if not asignaturas:
            print("No está inscrito en ninguna asignatura.")
            input("\nPresione Enter para continuar...")
            return
        
        print(f"{'Asignatura':<40} {'Promedio Final':<15} {'Estado':<10}")
        print("─" * 70)
        
        for id_asig, codigo, nombre, creditos, profesor in asignaturas:
            promedio = self.servicio.calcular_promedio_final(
                self.usuario_actual.id, id_asig
            )
            estado = "Aprobado" if promedio >= 3.0 else "Reprobado"
            color = "✓" if promedio >= 3.0 else "✗"
            
            print(f"{nombre:<40} {promedio:<15.2f} {color} {estado}")
        
        input("\nPresione Enter para continuar...")
    
    def simular_notas(self):
        #simular escenarios de notas
        self.mostrar_encabezado("SIMULADOR DE NOTAS")
        
        #seleccionar asignatura
        asignaturas = self.db.obtener_asignaturas_estudiante(self.usuario_actual.id)
        
        if not asignaturas:
            print("No está inscrito en ninguna asignatura.")
            input("\nPresione Enter para continuar...")
            return
        
        print("Asignaturas:")
        for i, (id_asig, codigo, nombre, creditos, profesor) in enumerate(asignaturas, 1):
            print(f"{i}. {codigo} - {nombre}")
        
        try:
            idx = int(input("\nSeleccione asignatura: ")) - 1
            asignatura_id = asignaturas[idx][0]
            asignatura_nombre = asignaturas[idx][2]
        except:
            print("\n✗ Selección inválida.")
            input("\nPresione Enter para continuar...")
            return
        
        try:
            nota_objetivo = float(input("\n¿Qué nota final desea obtener? (0.0 - 5.0): "))
            
            if not self.logica.validar_nota(nota_objetivo):
                print("\n✗ La nota debe estar entre 0.0 y 5.0")
                input("\nPresione Enter para continuar...")
                return
            
            resultado = self.servicio.simular_nota_necesaria(
                self.usuario_actual.id, asignatura_id, nota_objetivo
            )
            
            print(f"\n{'═' * 70}")
            print(f"SIMULACIÓN PARA {asignatura_nombre}")
            print(f"{'═' * 70}")
            print(f"Promedio actual: {resultado['promedio_actual']:.2f}")
            print(f"Nota objetivo: {resultado['nota_objetivo']:.2f}")
            print(f"Porcentaje completado: {resultado['porcentaje_completado']:.1f}%")
            print(f"Porcentaje faltante: {resultado['porcentaje_faltante']:.1f}%")
            print(f"\nNota necesaria en actividades restantes: {resultado['nota_necesaria']:.2f}")
            
            if resultado['es_alcanzable']:
                print("✓ ¡Es alcanzable!")
            else:
                print("✗ No es alcanzable con las actividades restantes, cancele materia bro")
            
        except ValueError:
            print("\n✗ Valor inválido.")
        
        input("\nPresione Enter para continuar...")
    
    def crear_apelacion(self):
        #crear una apelación
        self.mostrar_encabezado("CREAR APELACIÓN")
        
        try:
            nota_id = int(input("ID de la nota a apelar: "))
            
            #verificar que la nota existe Y pertenece al estudiante
            conn = self.db.obtener_conexion()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT estudiante_id, fecha_registro FROM notas WHERE id = ?",
                (nota_id,)
            )
            resultado = cursor.fetchone()
            conn.close()
            
            if not resultado:
                print("\n✗ Nota no encontrada.")
                input("\nPresione Enter para continuar...")
                return
            
            estudiante_id, fecha_registro_str = resultado
            
            if estudiante_id != self.usuario_actual.id:
                print("\n✗ Esta nota no le pertenece.")
                input("\nPresione Enter para continuar...")
                return
            
            fecha_nota = datetime.fromisoformat(fecha_registro_str)
            fecha_actual = datetime.now()
            
            #validar plazo usando logica formal
            if not self.logica.dentro_plazo_apelacion(fecha_nota, fecha_actual, 5):
                print("\n✗ El plazo para apelar esta nota ha expirado (máximo 5 días).")
                input("\nPresione Enter para continuar...")
                return
            
            descripcion = input("\nDescripción de la apelación (mín. 50 caracteres): ").strip()
            
            if not self.logica.validar_apelacion(descripcion):
                print("\n✗ La apelación debe tener al menos 50 caracteres y estar bien fundamentada.")
                input("\nPresione Enter para continuar...")
                return
            
            apelacion = Apelacion(
                id=None,
                nota_id=nota_id,
                estudiante_id=self.usuario_actual.id,
                descripcion=descripcion,
                estado=EstadoApelacion.PENDIENTE,
                fecha_creacion=datetime.now(),
                respuesta_profesor=None,
                fecha_respuesta=None
            )
            
            apelacion_id = self.db.crear_apelacion(apelacion)
            print(f"\n✓ Apelación creada exitosamente (ID: {apelacion_id})")
            
        except ValueError:
            print("\n✗ ID inválido.")
        
        input("\nPresione Enter para continuar...")
    
    def ver_mis_apelaciones(self):
        #apelaciones del estudiante
        self.mostrar_encabezado("MIS APELACIONES")
        
        apelaciones = self.db.obtener_apelaciones_estudiante(self.usuario_actual.id)
        
        if not apelaciones:
            print("No tiene apelaciones registradas.")
            input("\nPresione Enter para continuar...")
            return
        
        for apel in apelaciones:
            print(f"\n{'═' * 70}")
            print(f"ID: {apel.id} | Estado: {apel.estado.value.upper()}")
            print(f"Fecha creación: {apel.fecha_creacion.strftime('%Y-%m-%d %H:%M')}")
            print(f"{'─' * 70}")
            print(f"Su solicitud:\n{apel.descripcion}")
            
            if apel.respuesta_profesor:
                print(f"\n{'─' * 70}")
                print(f"Respuesta del profesor ({apel.fecha_respuesta.strftime('%Y-%m-%d %H:%M')}):")
                print(f"{apel.respuesta_profesor}")
        
        print(f"\n{'═' * 70}")
        input("\nPresione Enter para continuar...")


if __name__ == "__main__":
    try:
        app = InterfazCLI()
        app.iniciar()
    except KeyboardInterrupt:
        print("\n\n✓ Sistema cerrado correctamente.")
    except Exception as e:
        print(f"\n✗ Error del sistema: {e}")
        import traceback
        traceback.print_exc()