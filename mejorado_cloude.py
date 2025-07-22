import streamlit as st
import datetime
import pandas as pd
import json
import os
import base64
import hashlib
from typing import Dict, List, Optional

# --- Configuración de la página ---
st.set_page_config(
    page_title="Revisión de Columnas", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Estados de sesión ---
def init_session_state():
    """Inicializa todos los estados de sesión necesarios"""
    if 'revisiones_guardadas' not in st.session_state:
        st.session_state.revisiones_guardadas = []
    if 'editando_idx' not in st.session_state:
        st.session_state.editando_idx = None
    if 'usuario_logueado' not in st.session_state:
        st.session_state.usuario_logueado = None
    if 'proyecto_activo' not in st.session_state:
        st.session_state.proyecto_activo = None

init_session_state()

# --- Utilidades de seguridad ---
def hash_password(password: str) -> str:
    """Genera un hash seguro de la contraseña"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    """Verifica si la contraseña coincide con el hash"""
    return hash_password(password) == hashed

# --- Utilidades para persistencia ---
RUTA_PROYECTOS = "proyectos.json"

def cargar_proyectos() -> Dict:
    """Carga proyectos desde archivo JSON con manejo de errores mejorado"""
    if not os.path.exists(RUTA_PROYECTOS):
        return {}
    
    try:
        with open(RUTA_PROYECTOS, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Procesar datos cargados
        for usuario, info in data.items():
            # Decodificar fotos de perfil
            if info.get('foto_perfil') and isinstance(info['foto_perfil'], str):
                try:
                    info['foto_perfil'] = base64.b64decode(info['foto_perfil'])
                except Exception:
                    info['foto_perfil'] = None
            
            # Procesar revisiones
            if 'revisiones' in info:
                for rev in info['revisiones']:
                    # Convertir fechas string a objetos date
                    if 'fecha_revision' in rev and isinstance(rev['fecha_revision'], str):
                        try:
                            rev['fecha_revision'] = datetime.datetime.fromisoformat(rev['fecha_revision']).date()
                        except Exception:
                            rev['fecha_revision'] = datetime.date.today()
                    
                    # Decodificar fotos de revisiones
                    if rev.get('foto') and isinstance(rev['foto'], str):
                        try:
                            rev['foto'] = base64.b64decode(rev['foto'])
                        except Exception:
                            rev['foto'] = None
        
        return data
    
    except Exception as e:
        st.error(f"Error al cargar proyectos: {str(e)}. Se reiniciará el archivo.")
        return {}

def guardar_proyectos(data: Dict) -> bool:
    """Guarda proyectos en archivo JSON con validación"""
    try:
        # Crear copia para modificar sin afectar original
        data_to_save = {}
        
        for usuario, info in data.items():
            user_data = info.copy()
            
            # Codificar foto de perfil
            if user_data.get('foto_perfil'):
                if hasattr(user_data['foto_perfil'], 'getvalue'):
                    user_data['foto_perfil'] = user_data['foto_perfil'].getvalue()
                if isinstance(user_data['foto_perfil'], bytes):
                    user_data['foto_perfil'] = base64.b64encode(user_data['foto_perfil']).decode('utf-8')
            
            # Procesar revisiones
            if 'revisiones' in user_data:
                revisiones_procesadas = []
                for rev in user_data['revisiones']:
                    rev_copy = rev.copy()
                    
                    # Convertir fecha a string
                    if 'fecha_revision' in rev_copy and hasattr(rev_copy['fecha_revision'], 'isoformat'):
                        rev_copy['fecha_revision'] = rev_copy['fecha_revision'].isoformat()
                    
                    # Codificar foto
                    if rev_copy.get('foto'):
                        if hasattr(rev_copy['foto'], 'getvalue'):
                            rev_copy['foto'] = rev_copy['foto'].getvalue()
                        if isinstance(rev_copy['foto'], bytes):
                            rev_copy['foto'] = base64.b64encode(rev_copy['foto']).decode('utf-8')
                        else:
                            rev_copy['foto'] = None
                    
                    revisiones_procesadas.append(rev_copy)
                
                user_data['revisiones'] = revisiones_procesadas
            
            data_to_save[usuario] = user_data
        
        with open(RUTA_PROYECTOS, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        
        return True
    
    except Exception as e:
        st.error(f"Error al guardar proyectos: {str(e)}")
        return False

def guardar_revisiones_usuario():
    """Actualiza las revisiones del usuario en el archivo de proyectos"""
    proyectos = cargar_proyectos()
    usuario = st.session_state.usuario_logueado
    if usuario and usuario in proyectos:
        proyectos[usuario]['revisiones'] = st.session_state.revisiones_guardadas
        return guardar_proyectos(proyectos)
    return False

# --- Validaciones ---
def validar_campos_obligatorios(nombre: str, piso: str) -> bool:
    """Valida que los campos obligatorios no estén vacíos"""
    if not nombre.strip():
        st.error("❌ El nombre de la columna es obligatorio")
        return False
    if not piso.strip():
        st.error("❌ El piso es obligatorio")
        return False
    return True

def validar_credenciales(usuario: str, contrasena: str, correo: str = None) -> bool:
    """Valida formato de credenciales"""
    if len(usuario) < 3:
        st.error("❌ El usuario debe tener al menos 3 caracteres")
        return False
    if len(contrasena) < 6:
        st.error("❌ La contraseña debe tener al menos 6 caracteres")
        return False
    if correo and "@" not in correo:
        st.error("❌ Ingrese un correo electrónico válido")
        return False
    return True

# --- Funciones de utilidad para la interfaz ---
def limpiar_formulario():
    """Resetea el estado de edición"""
    st.session_state.editando_idx = None

def cargar_para_editar(idx: int):
    """Prepara el estado para editar una revisión"""
    st.session_state.editando_idx = idx

def is_mobile():
    """Detecta si es un dispositivo móvil (aproximación)"""
    # En Streamlit no hay acceso directo al user agent, 
    # pero podemos usar el ancho de pantalla como proxy
    return True  # Por simplicidad, asumimos optimización móvil siempre

# --- APLICACIÓN PRINCIPAL ---

proyectos = cargar_proyectos()

# Sidebar con opciones
st.sidebar.image("https://via.placeholder.com/200x80/1f77b4/white?text=OBRAS", width=200)
opcion = st.sidebar.radio("Seleccione una opción:", ["Ingresar al proyecto", "Registrar un proyecto"])

# --- REGISTRO ---
if opcion == "Registrar un proyecto":
    st.header("🏗️ Registro de Proyecto y Usuario")
    
    with st.form("registro_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            usuario = st.text_input("Usuario*", help="Mínimo 3 caracteres")
            contrasena = st.text_input("Contraseña*", type="password", help="Mínimo 6 caracteres")
            correo = st.text_input("Correo electrónico*")
        
        with col2:
            nombre_proyecto = st.text_input("Nombre del proyecto*")
            pisos = st.number_input("¿Cuántos pisos tiene la edificación?", min_value=1, step=1, value=1)
            tiene_sotanos = st.radio("¿Hay sótanos?", ["No", "Sí"])
        
        if tiene_sotanos == "Sí":
            num_sotanos = st.number_input("¿Cuántos sótanos?", min_value=1, step=1, value=1)
        else:
            num_sotanos = 0
        
        foto_perfil = st.file_uploader("Foto de perfil del proyecto", type=["jpg", "jpeg", "png"])
        
        submitted = st.form_submit_button("🚀 Registrar proyecto", use_container_width=True)
        
        if submitted:
            if validar_credenciales(usuario, contrasena, correo):
                if usuario in proyectos:
                    st.error("❌ El usuario ya existe. Elija otro nombre de usuario.")
                else:
                    # Crear nuevo proyecto
                    proyectos[usuario] = {
                        "contrasena": hash_password(contrasena),  # Hash de la contraseña
                        "correo": correo,
                        "nombre_proyecto": nombre_proyecto,
                        "pisos": pisos,
                        "tiene_sotanos": tiene_sotanos == "Sí",
                        "num_sotanos": num_sotanos,
                        "foto_perfil": foto_perfil.getvalue() if foto_perfil else None,
                        "revisiones": []
                    }
                    
                    if guardar_proyectos(proyectos):
                        st.success("✅ Proyecto y usuario registrados correctamente. Ahora puede ingresar.")
                        st.balloons()
                    else:
                        st.error("❌ Error al guardar el proyecto. Intente nuevamente.")

# --- LOGIN ---
elif opcion == "Ingresar al proyecto":
    st.header("🔐 Ingreso al Proyecto")
    
    with st.form("login_form"):
        usuario = st.text_input("Usuario")
        contrasena = st.text_input("Contraseña", type="password")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            submitted = st.form_submit_button("🚪 Ingresar", use_container_width=True)
        
        if submitted:
            if usuario in proyectos and verify_password(contrasena, proyectos[usuario]["contrasena"]):
                st.session_state.usuario_logueado = usuario
                st.session_state.proyecto_activo = proyectos[usuario]
                # Cargar revisiones del usuario
                st.session_state.revisiones_guardadas = proyectos[usuario].get('revisiones', [])
                st.success(f"✅ Bienvenido, {usuario}! Proyecto: {proyectos[usuario]['nombre_proyecto']}")
                st.balloons()
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos.")

# --- APLICACIÓN PRINCIPAL (Usuario logueado) ---
if st.session_state.usuario_logueado and st.session_state.proyecto_activo:
    proyecto = st.session_state.proyecto_activo
    
    # Header con info del proyecto
    st.sidebar.success(f"🏗️ {proyecto['nombre_proyecto']}")
    st.sidebar.info(f"👤 Usuario: {st.session_state.usuario_logueado}")
    
    if st.sidebar.button("🚪 Cerrar Sesión"):
        # Limpiar estados de sesión
        for key in ['usuario_logueado', 'proyecto_activo', 'revisiones_guardadas', 'editando_idx']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
    
    st.title("🏗️ App de Revisión de Columnas")
    
    # Mostrar foto del proyecto si existe
    if proyecto.get('foto_perfil'):
        st.sidebar.image(proyecto['foto_perfil'], caption="Proyecto", width=200)
    
    # Información del proyecto
    with st.expander("ℹ️ Información del Proyecto", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Pisos", proyecto['pisos'])
        with col2:
            st.metric("Sótanos", proyecto['num_sotanos'] if proyecto['tiene_sotanos'] else 0)
        with col3:
            total_revisiones = len(st.session_state.revisiones_guardadas)
            st.metric("Total Revisiones", total_revisiones)
    
    # Verificar si estamos editando
    revision_a_editar = None
    if st.session_state.editando_idx is not None:
        if st.session_state.editando_idx < len(st.session_state.revisiones_guardadas):
            revision_a_editar = st.session_state.revisiones_guardadas[st.session_state.editando_idx]
            st.info(f"✍️ Editando: **{revision_a_editar['nombre']}** - Piso: **{revision_a_editar['piso']}**")
        else:
            st.session_state.editando_idx = None
    
    # --- FORMULARIO DE REVISIÓN ---
    with st.form(key="revision_form", clear_on_submit=False):
        st.header("📋 Formulario de Revisión")
        
        # Campos básicos - adaptados para móvil
        if is_mobile():
            nombre = st.text_input(
                "Nombre de la Columna*", 
                value=revision_a_editar['nombre'] if revision_a_editar else "",
                help="Ej: C1, C-A1, Columna 1"
            )
            piso = st.text_input(
                "Piso*", 
                value=revision_a_editar['piso'] if revision_a_editar else "",
                help="Ej: PB, 1, 2, S1, S2"
            )
            fecha_revision = st.date_input(
                "Fecha de revisión",
                value=revision_a_editar.get('fecha_revision', datetime.date.today()) if revision_a_editar else datetime.date.today()
            )
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                nombre = st.text_input(
                    "Nombre de la Columna*", 
                    value=revision_a_editar['nombre'] if revision_a_editar else ""
                )
            with col2:
                piso = st.text_input(
                    "Piso*", 
                    value=revision_a_editar['piso'] if revision_a_editar else ""
                )
            with col3:
                fecha_revision = st.date_input(
                    "Fecha de revisión",
                    value=revision_a_editar.get('fecha_revision', datetime.date.today()) if revision_a_editar else datetime.date.today()
                )
        
        st.markdown("---")
        
        # Items de revisión
        items_a_revisar = {
            'estribos': 'Cantidad estribos',
            'longitudinal': 'Cantidad acero longitudinal',
            'recubrimiento': 'Recubrimiento',
            'posicion': 'Posición acero',
            'ejes': 'Ubicación columna (ejes)',
            'traslapo': 'Traslapo'
        }
        
        st.subheader("🔍 Puntos de Chequeo")
        datos_formulario = {}
        
        for key, label in items_a_revisar.items():
            with st.container():
                st.markdown(f"**{label}:**")
                
                if is_mobile():
                    # Layout vertical para móvil
                    default_value = revision_a_editar.get(f'cumple_{key}', 'Cumple') if revision_a_editar else "Cumple"
                    datos_formulario[f'cumple_{key}'] = st.radio(
                        f"Estado - {label}",
                        options=['Cumple', 'No cumple'],
                        index=0 if default_value == 'Cumple' else 1,
                        key=f'cumple_{key}',
                        horizontal=True
                    )
                    
                    if datos_formulario[f'cumple_{key}'] == 'No cumple':
                        default_obs = revision_a_editar.get(f'obs_{key}', '') if revision_a_editar else ''
                        datos_formulario[f'obs_{key}'] = st.text_area(
                            f"Observación - {label}", 
                            value=default_obs, 
                            key=f'obs_{key}',
                            height=80
                        )
                else:
                    # Layout horizontal para desktop
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        default_value = revision_a_editar.get(f'cumple_{key}', 'Cumple') if revision_a_editar else "Cumple"
                        datos_formulario[f'cumple_{key}'] = st.radio(
                            f"Estado",
                            options=['Cumple', 'No cumple'],
                            index=0 if default_value == 'Cumple' else 1,
                            key=f'cumple_{key}'
                        )
                    
                    with col2:
                        if datos_formulario[f'cumple_{key}'] == 'No cumple':
                            default_obs = revision_a_editar.get(f'obs_{key}', '') if revision_a_editar else ''
                            datos_formulario[f'obs_{key}'] = st.text_area(
                                "Observación de 'No Cumple'", 
                                value=default_obs, 
                                key=f'obs_{key}',
                                height=68
                            )
        
        st.markdown("---")
        
        # Foto y observaciones
        st.subheader("📸 Documentación")
        
        if is_mobile():
            # Layout vertical para móvil
            st.markdown("**Foto de la columna:**")
            foto_subida = st.file_uploader(
                "Subir foto desde el dispositivo", 
                type=["jpg", "jpeg", "png"], 
                key="foto_subida"
            )
            
            if revision_a_editar and revision_a_editar.get('foto'):
                st.write("📷 Foto guardada anteriormente:")
                st.image(revision_a_editar['foto'], width=300)
            
            observaciones = st.text_area(
                "Observaciones generales",
                value=revision_a_editar.get('observaciones', '') if revision_a_editar else "",
                height=120
            )
        else:
            # Layout horizontal para desktop
            col_foto, col_obs = st.columns(2)
            
            with col_foto:
                st.markdown("**Foto de la columna:**")
                foto_subida = st.file_uploader(
                    "Subir foto desde el dispositivo", 
                    type=["jpg", "jpeg", "png"], 
                    key="foto_subida"
                )
                
                if revision_a_editar and revision_a_editar.get('foto'):
                    st.write("📷 Foto guardada anteriormente:")
                    st.image(revision_a_editar['foto'])
            
            with col_obs:
                observaciones = st.text_area(
                    "Observaciones generales",
                    value=revision_a_editar.get('observaciones', '') if revision_a_editar else "",
                    height=150
                )
        
        # Campo de corrección (solo si estamos editando y hay items "No cumple")
        obs_correccion = ""
        if revision_a_editar and any(v == 'No cumple' for k, v in revision_a_editar.items() if k.startswith('cumple_')):
            obs_correccion = st.text_area(
                "📝 Observaciones de la corrección",
                help="Describa aquí la corrección realizada para los ítems que estaban en 'No Cumple'.",
                height=100
            )
        
        # Botones del formulario
        col_submit, col_cancel = st.columns([2, 1])
        
        with col_submit:
            if revision_a_editar:
                submitted = st.form_submit_button("💾 Actualizar Revisión", use_container_width=True)
            else:
                submitted = st.form_submit_button("💾 Guardar Revisión", use_container_width=True)
        
        with col_cancel:
            if st.form_submit_button("❌ Cancelar", use_container_width=True):
                limpiar_formulario()
                st.rerun()
        
        # --- LÓGICA DE GUARDADO ---
        if submitted:
            if validar_campos_obligatorios(nombre, piso):
                # Crear nueva revisión
                nueva_revision = {
                    'nombre': nombre.strip(),
                    'piso': piso.strip(),
                    'fecha_revision': fecha_revision,
                    'observaciones': observaciones.strip(),
                    'historial': revision_a_editar.get('historial', []) if revision_a_editar else []
                }
                
                # Agregar datos de chequeo
                for key in items_a_revisar.keys():
                    nueva_revision[f'cumple_{key}'] = datos_formulario[f'cumple_{key}']
                    nueva_revision[f'obs_{key}'] = datos_formulario.get(f'obs_{key}', '').strip()
                
                # Manejar foto
                if foto_subida:
                    nueva_revision['foto'] = foto_subida.getvalue()
                elif revision_a_editar:
                    nueva_revision['foto'] = revision_a_editar.get('foto')
                else:
                    nueva_revision['foto'] = None
                
                # Si estamos editando, manejar historial
                if st.session_state.editando_idx is not None:
                    anterior = st.session_state.revisiones_guardadas[st.session_state.editando_idx]
                    
                    # Registrar correcciones en el historial
                    for key, label in items_a_revisar.items():
                        if (anterior.get(f'cumple_{key}') == 'No cumple' and 
                            nueva_revision[f'cumple_{key}'] == 'Cumple'):
                            
                            cambio = (f"{label} corregido. "
                                    f"Obs. anterior: '{anterior.get(f'obs_{key}', 'Sin observación')}'. "
                                    f"Obs. corrección: '{obs_correccion}'")
                            nueva_revision['historial'].append(f"[{datetime.date.today()}] {cambio}")
                    
                    # Actualizar revisión existente
                    st.session_state.revisiones_guardadas[st.session_state.editando_idx] = nueva_revision
                    
                    if guardar_revisiones_usuario():
                        st.success("✅ Revisión actualizada con éxito!")
                        st.balloons()
                        limpiar_formulario()
                        st.rerun()
                    else:
                        st.error("❌ Error al actualizar la revisión")
                else:
                    # Agregar nueva revisión
                    st.session_state.revisiones_guardadas.append(nueva_revision)
                    
                    if guardar_revisiones_usuario():
                        st.success("✅ Revisión guardada con éxito!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Error al guardar la revisión")
    
    # --- REVISIONES ARCHIVADAS ---
    st.markdown("---")
    st.header("📚 Revisiones Archivadas")
    
    if not st.session_state.revisiones_guardadas:
        st.info("📭 Aún no hay revisiones guardadas. Cree su primera revisión usando el formulario anterior.")
    else:
        # Estadísticas rápidas
        total_revisiones = len(st.session_state.revisiones_guardadas)
        revisiones_con_problemas = sum(1 for rev in st.session_state.revisiones_guardadas 
                                     if any(v == 'No cumple' for k, v in rev.items() if k.startswith('cumple_')))
        revisiones_ok = total_revisiones - revisiones_con_problemas
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total", total_revisiones)
        with col2:
            st.metric("✅ Conformes", revisiones_ok)
        with col3:
            st.metric("❌ Con observaciones", revisiones_con_problemas)
        
        # Agrupar por piso
        revisiones_por_piso = {}
        for i, rev in enumerate(st.session_state.revisiones_guardadas):
            piso = str(rev.get('piso', 'Sin piso'))
            if piso not in revisiones_por_piso:
                revisiones_por_piso[piso] = []
            revisiones_por_piso[piso].append((i, rev))
        
        # Selector de piso
        pisos_ordenados = sorted(revisiones_por_piso.keys())
        piso_seleccionado = st.selectbox(
            "🏢 Selecciona el piso para ver sus revisiones:", 
            pisos_ordenados,
            help="Filtra las revisiones por piso para una mejor organización"
        )
        
        # Mostrar revisiones del piso seleccionado
        st.subheader(f"Revisiones - Piso {piso_seleccionado}")
        
        for i, rev in revisiones_por_piso[piso_seleccionado]:
            hay_no_cumple = any(v == 'No cumple' for k, v in rev.items() if k.startswith('cumple_'))
            estado_emoji = "❌" if hay_no_cumple else "✅"
            
            with st.expander(f"{estado_emoji} **{rev['nombre']}** | Fecha: **{rev['fecha_revision']}**"):
                # Información básica
                col_info, col_actions = st.columns([3, 1])
                
                with col_info:
                    st.markdown(f"**📅 Fecha:** {rev['fecha_revision']}")
                    st.markdown(f"**🏢 Piso:** {rev['piso']}")
                    
                    if rev.get('observaciones'):
                        st.markdown(f"**💭 Observaciones:** {rev['observaciones']}")
                
                with col_actions:
                    if st.button("✍️ Editar", key=f"edit_{i}", use_container_width=True):
                        cargar_para_editar(i)
                        st.rerun()
                    
                    if st.button("🗑️ Eliminar", key=f"delete_{i}", use_container_width=True):
                        if st.session_state.get(f'confirm_delete_{i}'):
                            st.session_state.revisiones_guardadas.pop(i)
                            guardar_revisiones_usuario()
                            st.success("Revisión eliminada")
                            st.rerun()
                        else:
                            st.session_state[f'confirm_delete_{i}'] = True
                            st.warning("Presione nuevamente para confirmar eliminación")
                
                st.markdown("**🔍 Detalle de chequeos:**")
                
                # Mostrar items con formato mejorado
                items_cumple = []
                items_no_cumple = []
                
                for key, label in items_a_revisar.items():
                    estado = rev.get(f'cumple_{key}', 'N/A')
                    obs = rev.get(f'obs_{key}', '')
                    
                    item_info = {'label': label, 'obs': obs}
                    
                    if estado == 'Cumple':
                        items_cumple.append(item_info)
                    else:
                        items_no_cumple.append(item_info)
                
                # Mostrar items que cumplen
                if items_cumple:
                    st.success("**✅ Elementos que cumplen:**")
                    for item in items_cumple:
                        st.markdown(f"• {item['label']}")
                
                # Mostrar items que no cumplen
                if items_no_cumple:
                    st.error("**❌ Elementos que NO cumplen:**")
                    for item in items_no_cumple:
                        st.markdown(f"• **{item['label']}**")
                        if item['obs']:
                            st.markdown(f"  💭 *{item['obs']}*")
                
                # Mostrar foto
                if rev.get('foto'):
                    st.markdown("**📸 Foto:**")
                    foto = rev['foto']
                    
                    # Manejar diferentes formatos de foto
                    if isinstance(foto, str):
                        try:
                            foto = base64.b64decode(foto)
                        except Exception:
                            foto = None
                    
                    if isinstance(foto, bytes):
                        st.image(foto, caption="Foto de la revisión", width=400)
                
                # Historial de correcciones
                if rev.get('historial'):
                    st.markdown("**📝 Historial de correcciones:**")
                    for entrada in rev['historial']:
                        st.info(f"📌 {entrada}")

else:
    # Mostrar información cuando no hay usuario logueado
    st.markdown("""
    # 🏗️ Bienvenido a la App de Revisión de Columnas
    
    Una herramienta diseñada específicamente para supervisores técnicos de obra que necesitan:
    
    ✅ **Revisar columnas de forma sistemática**  
    ✅ **Documentar con fotos desde dispositivos móviles**  
    ✅ **Llevar un historial de correcciones**  
    ✅ **Acceder desde cualquier dispositivo**  
    
    ## 🚀 Para comenzar:
    
    1. **Si es nuevo:** Use "Registrar un proyecto" en el menú lateral
    2. **Si ya tiene cuenta:** Use "Ingresar al proyecto"
    
    ## 📱 Optimizado para:
    - Teléfonos móviles
    - Tabletas
    - Computadoras de escritorio
    
    ---
    *Desarrollado para ingenieros civiles y supervisores técnicos*
    """)

# --- PIE DE PÁGINA ---
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
    🏗️ App de Revisión de Columnas v2.0 - Optimizada para obra
    </div>
    """, 
    unsafe_allow_html=True
)