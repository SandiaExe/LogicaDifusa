# -*- coding: utf-8 -*-

from flask import Flask, render_template, request
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

app = Flask(__name__)

# --- Variables del Sistema Fuzzy ---

# Antecedentes (Entradas)
# "Atractivo" (antes Calidad) - Atractivo del Producto (0-10)
atractivo = ctrl.Antecedent(np.arange(0, 10.1, 0.1), 'atractivo')
# "Disponibilidad" (antes Stock) - Cantidad disponible o capacidad de producción (1-100)
disponibilidad = ctrl.Antecedent(np.arange(1, 100.1, 1), 'disponibilidad')

# Consecuente (Salida)
# "ExitoPotencial" (antes Descuento) - Nivel de Éxito Proyectado (0-100%)
exito_potencial = ctrl.Consequent(np.arange(0, 100.1, 0.1), 'exito_potencial')

# --- Funciones de Membresía Modificadas ---

# Atractivo (Calidad)
atractivo['bajo'] = fuzz.trimf(atractivo.universe, [0, 0, 5])
atractivo['promedio'] = fuzz.trimf(atractivo.universe, [3, 6, 9])
atractivo['sobresaliente'] = fuzz.trimf(atractivo.universe, [7, 10, 10])

# Disponibilidad (Stock)
disponibilidad['limitada'] = fuzz.trimf(disponibilidad.universe, [1, 1, 50])
disponibilidad['adecuada'] = fuzz.trimf(disponibilidad.universe, [30, 70, 90])
disponibilidad['abundante'] = fuzz.trimf(disponibilidad.universe, [70, 100, 100])

# Exito Potencial (Descuento)
exito_potencial['bajo'] = fuzz.trimf(exito_potencial.universe, [0, 15, 30])
exito_potencial['moderado'] = fuzz.trimf(exito_potencial.universe, [20, 50, 80])
exito_potencial['alto'] = fuzz.trimf(exito_potencial.universe, [70, 90, 100])

# --- Reglas de Inferencia (Lógica de Éxito) ---
# Ahora las reglas reflejan la lógica para maximizar el éxito:
rules = [
    # Si el atractivo es bajo, el éxito es bajo, independientemente de la disponibilidad.
    ctrl.Rule(atractivo['bajo'], exito_potencial['bajo']),
    
    # Buen atractivo con disponibilidad abundante = Éxito Alto
    ctrl.Rule(atractivo['sobresaliente'] & disponibilidad['abundante'], exito_potencial['alto']),
    
    # Atractivo sobresaliente pero disponibilidad limitada = Éxito Moderado (debido a la limitación)
    ctrl.Rule(atractivo['sobresaliente'] & disponibilidad['limitada'], exito_potencial['moderado']),
    
    # Atractivo promedio y disponibilidad adecuada = Éxito Moderado
    ctrl.Rule(atractivo['promedio'] & disponibilidad['adecuada'], exito_potencial['moderado']),
    
    # Atractivo promedio con disponibilidad abundante = Éxito Alto
    ctrl.Rule(atractivo['promedio'] & disponibilidad['abundante'], exito_potencial['alto']),
    
    # Atractivo promedio con disponibilidad limitada = Éxito Bajo/Moderado
    ctrl.Rule(atractivo['promedio'] & disponibilidad['limitada'], exito_potencial['bajo'])
]

# Creación del sistema de control
exito_ctrl = ctrl.ControlSystem(rules)
exito_sistema = ctrl.ControlSystemSimulation(exito_ctrl)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/proyectar', methods=['POST'])
def proyectar():
    # Obtener valores del formulario
    try:
        atractivo_val = float(request.form['atractivo'])
        disponibilidad_val = float(request.form['disponibilidad'])
        inversion_val = float(request.form['inversion'])
    except ValueError:
        return render_template('resultado.html', error="Error: Por favor, ingrese valores numéricos válidos.")

    # 1. Calcular el Nivel de Éxito Fuzzy (0-100)
    exito_sistema.input['atractivo'] = atractivo_val
    exito_sistema.input['disponibilidad'] = disponibilidad_val
    
    try:
        exito_sistema.compute()
        exito_porcentaje = exito_sistema.output['exito_potencial']
    except ValueError:
        # En caso de que no se pueda computar (e.g., input fuera de rango)
        return render_template('resultado.html', error="Error al calcular el potencial. Verifique los rangos de entrada.")


    # 2. Calcular la Proyección de Retorno Financiero
    # Usaremos el porcentaje de éxito para proyectar un Retorno sobre Inversión (ROI)
    # Proyección: ROI = Inversión * (Éxito Porcentaje / 50) - (Un factor de riesgo)
    
    # Normalización del éxito (ej: 100% éxito -> factor de 2.0. 50% éxito -> factor de 1.0)
    factor_retorno = exito_porcentaje / 50.0 
    
    # El retorno es la inversión multiplicada por el factor de retorno.
    retorno_proyectado = inversion_val * factor_retorno
    
    # Ganancia Neta Proyectada = Retorno Total - Inversión Inicial
    ganancia_neta = retorno_proyectado - inversion_val
    
    # Formateo del resultado principal
    if exito_porcentaje < 35:
        nivel_texto = "Bajo"
        color_clase = "text-red-600 border-red-600 bg-red-50"
        mensaje_clave = "Riesgo alto. Se recomienda revisar el Atractivo o la Disponibilidad."
    elif exito_porcentaje < 75:
        nivel_texto = "Moderado"
        color_clase = "text-yellow-600 border-yellow-600 bg-yellow-50"
        mensaje_clave = "Potencial equilibrado. Se sugiere optimizar la Disponibilidad."
    else:
        nivel_texto = "Alto"
        color_clase = "text-green-600 border-green-600 bg-green-50"
        mensaje_clave = "¡Excelente proyección! Continuar con la estrategia actual."

    # Devolver el resultado a la nueva plantilla
    return render_template('resultado.html', 
        atractivo=atractivo_val,
        disponibilidad=disponibilidad_val,
        inversion=inversion_val,
        exito_porcentaje=f"{exito_porcentaje:.1f}",
        nivel_texto=nivel_texto,
        color_clase=color_clase,
        mensaje_clave=mensaje_clave,
        retorno_proyectado=f"{retorno_proyectado:.2f}",
        ganancia_neta=f"{ganancia_neta:.2f}"
    )

if __name__ == '__main__':
    # Nota: En entornos de producción se usaría un servidor WSGI (Gunicorn, uWSGI)
    app.run(debug=True)
