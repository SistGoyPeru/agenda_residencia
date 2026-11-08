from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required, login_not_required
from django.db.models import Count, ProtectedError, Q, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    MovimientoCuponForm,
    PerfilForm,
    ProductoForm,
    RegistroForm,
    ResidenciaForm,
    VisitaForm,
    VisitaProductoFormSet,
    ZonaForm,
)
from .models import (
    MovimientoCupon,
    Perfil,
    Producto,
    Residencia,
    Visita,
    VisitaProducto,
    Zona,
    perfil_de,
    rango_semana,
    siguiente_residencia,
)

TIPOS_LOGO = ("image/png", "image/jpeg", "image/webp")


def tipo_de_imagen(datos):
    if datos.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if datos.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if datos[:4] == b"RIFF" and datos[8:12] == b"WEBP":
        return "image/webp"
    return None


def estado_plan(usuario):
    perfil = perfil_de(usuario)
    usadas = Residencia.objects.filter(propietario=usuario).count()
    limite = perfil.limite_residencias
    return {
        "perfil": perfil,
        "residencias_usadas": usadas,
        "limite_residencias": limite,
        "puede_agregar": limite is None or usadas < limite,
    }


def productos_con_stock(usuario, solo_activos=True):
    """Lista de productos del usuario con las cifras de cupones calculadas."""
    queryset = Producto.objects.filter(propietario=usuario)
    if solo_activos:
        queryset = queryset.filter(activo=True)
    productos = list(queryset)

    cargados = {
        fila["producto_id"]: fila["total"]
        for fila in MovimientoCupon.objects.filter(producto__propietario=usuario)
        .values("producto_id")
        .annotate(total=Sum("cantidad"))
    }
    usados = {
        fila["producto_id"]: fila["total"]
        for fila in VisitaProducto.objects.filter(
            visita__residencia__propietario=usuario,
            visita__estado=Visita.Estado.ENTREGADA,
        )
        .values("producto_id")
        .annotate(total=Sum("cupones"))
    }

    for producto in productos:
        producto.cargados = cargados.get(producto.pk, 0)
        producto.usados = usados.get(producto.pk, 0)
        producto.stock = producto.cargados - producto.usados
        producto.bajo = producto.stock <= producto.stock_minimo
        if producto.cargados > 0:
            producto.porcentaje = max(
                0, min(100, round(producto.stock * 100 / producto.cargados))
            )
        else:
            producto.porcentaje = 0
    return productos


def cupones_usados_en(usuario, inicio, fin):
    return (
        VisitaProducto.objects.filter(
            visita__residencia__propietario=usuario,
            visita__estado=Visita.Estado.ENTREGADA,
            visita__fecha__range=(inicio, fin),
        ).aggregate(total=Sum("cupones"))["total"]
        or 0
    )


def pendientes_de_la_semana(usuario, referencia):
    """Residencias del usuario a las que les faltan visitas por planificar.

    La ruta no tiene dÃ­as fijos: se cuenta lo entregado y lo ya programado
    dentro de la semana, y solo se avisa de lo que queda por cubrir.
    """
    inicio, fin = rango_semana(referencia)

    def contar(estado):
        return {
            fila["residencia_id"]: fila["total"]
            for fila in Visita.objects.filter(
                residencia__propietario=usuario,
                estado=estado,
                fecha__range=(inicio, fin),
            )
            .values("residencia_id")
            .annotate(total=Count("id"))
        }

    entregadas = contar(Visita.Estado.ENTREGADA)
    programadas = contar(Visita.Estado.PENDIENTE)
    filas = []
    for residencia in (
        Residencia.objects.filter(propietario=usuario, activo=True)
        .select_related("zona")
    ):
        hechas = entregadas.get(residencia.pk, 0)
        planificadas = programadas.get(residencia.pk, 0)
        faltan = residencia.frecuencia_semanal - hechas - planificadas
        if faltan > 0:
            filas.append(
                {
                    "residencia": residencia,
                    "hechas": hechas,
                    "programadas": planificadas,
                    "faltan": faltan,
                }
            )
    filas.sort(
        key=lambda fila: (
            fila["residencia"].zona.orden if fila["residencia"].zona else 999,
            fila["residencia"].orden_ruta,
            fila["residencia"].nombre,
        )
    )
    return filas


def resumen_semana(usuario, referencia=None):
    """Progreso de la semana: visitas entregadas frente a las previstas."""
    inicio, fin = rango_semana(referencia)
    previstas = (
        Residencia.objects.filter(propietario=usuario, activo=True).aggregate(
            total=Sum("frecuencia_semanal")
        )["total"]
        or 0
    )
    hechas = Visita.objects.filter(
        residencia__propietario=usuario,
        estado=Visita.Estado.ENTREGADA,
        fecha__range=(inicio, fin),
    ).count()
    programadas = Visita.objects.filter(
        residencia__propietario=usuario,
        estado=Visita.Estado.PENDIENTE,
        fecha__range=(inicio, fin),
    ).count()
    return {
        "inicio": inicio,
        "fin": fin,
        "previstas": previstas,
        "hechas": hechas,
        "programadas": programadas,
        "porcentaje": (
            max(0, min(100, round(hechas * 100 / previstas))) if previstas else 0
        ),
    }


@login_not_required
def registro(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        login(request, usuario)
        messages.success(
            request, "Cuenta creada. Ya tienes tu agenda personal."
        )
        return redirect("dashboard")
    return render(request, "registration/registro.html", {"form": form})


def planes(request):
    return render(
        request, "residencias/planes.html", {"estado": estado_plan(request.user)}
    )


def mi_cuenta(request):
    perfil = perfil_de(request.user)
    form = PerfilForm(request.POST or None, request.FILES or None, instance=perfil)
    if request.method == "POST" and form.is_valid():
        if form.cleaned_data.get("quitar_logo"):
            perfil.logo = None
            perfil.logo_tipo = ""
            perfil.logo_actualizado = timezone.now()
        archivo = form.cleaned_data.get("logo")
        if archivo:
            datos = archivo.read()
            if len(datos) > 300 * 1024:
                form.add_error("logo", "El logo no puede superar 300 KB.")
            else:
                tipo = tipo_de_imagen(datos)
                if tipo not in TIPOS_LOGO:
                    form.add_error(
                        "logo", "Formato no vÃ¡lido. Usa PNG, JPG o WEBP."
                    )
                else:
                    perfil.logo = datos
                    perfil.logo_tipo = tipo
                    perfil.logo_actualizado = timezone.now()
        if not form.errors:
            form.save()
            messages.success(request, "Datos de la empresa guardados.")
            return redirect("mi_cuenta")
    return render(
        request,
        "residencias/mi_cuenta.html",
        {"form": form, "perfil": perfil, "estado": estado_plan(request.user)},
    )


def mi_logo(request):
    perfil = perfil_de(request.user)
    if not perfil.logo:
        raise Http404
    respuesta = HttpResponse(
        bytes(perfil.logo), content_type=perfil.logo_tipo or "image/png"
    )
    respuesta["Cache-Control"] = "private, max-age=86400"
    return respuesta


@login_required
def usuarios(request):
    if not request.user.is_staff:
        return redirect("dashboard")
    usuarios = get_user_model().objects.all().order_by("username")
    return render(
        request,
        "residencias/usuarios.html",
        {"usuarios": usuarios},
    )


@login_required
def usuario_crear(request):
    if not request.user.is_staff:
        return redirect("dashboard")
    Usuario = get_user_model()
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password") or request.POST.get("password1")
        if not username or not password:
            messages.error(request, "Usuario y clave son obligatorios.")
        elif Usuario.objects.filter(username=username).exists():
            messages.error(request, "Ese usuario ya existe.")
        else:
            usuario = Usuario.objects.create_user(
                username=username, email=email, password=password
            )
            Perfil.objects.get_or_create(usuario=usuario)
            messages.success(request, f"Usuario Â«{username}Â» creado.")
            return redirect("usuarios")
    return render(request, "residencias/usuario_form.html", {"accion": "crear"})


@login_required
def usuario_editar(request, pk):
    if not request.user.is_staff:
        return redirect("dashboard")
    Usuario = get_user_model()
    usuario = get_object_or_404(Usuario, pk=pk)
    perfil = Perfil.objects.get_or_create(usuario=usuario)[0]
    if request.method == "POST":
        usuario.email = request.POST.get("email", usuario.email)
        clave = request.POST.get("password")
        if clave:
            usuario.set_password(clave)
        usuario.save()
        perfil.plan = request.POST.get("plan") or perfil.plan
        perfil.activo_hasta = (
            date.fromisoformat(request.POST.get("activo_hasta"))
            if request.POST.get("activo_hasta")
            else None
        )
        perfil.empresa = request.POST.get("empresa") or ""
        perfil.cif = request.POST.get("cif") or ""
        perfil.telefono = request.POST.get("telefono") or ""
        perfil.email_contacto = request.POST.get("email_contacto") or ""
        perfil.direccion = request.POST.get("direccion") or ""
        perfil.web = request.POST.get("web") or ""
        perfil.save()
        messages.success(request, f"Usuario Â«{usuario.username}Â» actualizado.")
        return redirect("usuarios")
    return render(
        request,
        "residencias/usuario_form.html",
        {"usuario": usuario, "perfil": perfil, "accion": "editar"},
    )


@login_required
def usuario_borrar(request, pk):
    if not request.user.is_staff:
        return redirect("dashboard")
    Usuario = get_user_model()
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == "POST":
        usuario.delete()
        messages.success(request, f"Usuario Â«{usuario.username}Â» eliminado.")
        return redirect("usuarios")
    return render(
        request, "residencias/usuario_confirmar_borrado.html", {"usuario": usuario}
    )


@login_required
def usuario_activar_plan(request, pk):
    if not request.user.is_staff:
        return redirect("dashboard")
    Usuario = get_user_model()
    usuario = get_object_or_404(Usuario, pk=pk)
    perfil = Perfil.objects.get_or_create(usuario=usuario)[0]
    perfil.plan = "PRO"
    fin_actual = perfil.activo_hasta
    if fin_actual and fin_actual >= timezone.localdate():
        perfil.activo_hasta = fin_actual + timedelta(days=30)
    else:
        perfil.activo_hasta = timezone.localdate() + timedelta(days=30)
    perfil.save()
    messages.success(
        request, "Plan Pro activado para el usuario: " + usuario.username
    )
    return redirect("usuarios")


def dashboard(request):
    hoy = timezone.localdate()
    inicio, fin = rango_semana(hoy)
    visitas_hoy = list(
        Visita.objects.filter(residencia__propietario=request.user, fecha=hoy)
        .select_related("residencia", "residencia__zona")
        .order_by("turno", "residencia__zona__orden", "residencia__orden_ruta")
    )
    resumen_hoy = {
        "total": len(visitas_hoy),
        "entregadas": sum(v.estado == Visita.Estado.ENTREGADA for v in visitas_hoy),
        "pendientes": sum(v.estado == Visita.Estado.PENDIENTE for v in visitas_hoy),
        "incidencias": sum(v.estado == Visita.Estado.INCIDENCIA for v in visitas_hoy),
    }
    productos = productos_con_stock(request.user)
    contexto = {
        "hoy": hoy,
        "visitas_hoy": visitas_hoy,
        "resumen_hoy": resumen_hoy,
        "siguiente": siguiente_residencia(request.user, hoy),
        "pendientes": pendientes_de_la_semana(request.user, hoy),
        "semana": resumen_semana(request.user, hoy),
        "productos_bajos": [p for p in productos if p.bajo],
        "productos": productos,
        "cupones_semana": cupones_usados_en(request.user, inicio, fin),
        "total_cupones": sum(p.stock for p in productos),
        "estado": estado_plan(request.user),
    }
    return render(request, "residencias/dashboard.html", contexto)


def agenda(request):
    hoy = timezone.localdate()
    try:
        offset = int(request.GET.get("semana", "0"))
    except ValueError:
        offset = 0
    referencia = hoy + timedelta(weeks=offset)
    inicio, fin = rango_semana(referencia)

    dias = []
    for i in range(7):
        dia = inicio + timedelta(days=i)
        visitas = list(
            Visita.objects.filter(
                residencia__propietario=request.user, fecha=dia
            )
            .select_related("residencia", "residencia__zona")
            .order_by(
                "turno",
                "residencia__zona__orden",
                "residencia__orden_ruta",
                "residencia__nombre",
            )
        )
        dias.append({"fecha": dia, "visitas": visitas, "es_hoy": dia == hoy})

    contexto = {
        "hoy": hoy,
        "dias": dias,
        "inicio": inicio,
        "fin": fin,
        "offset": offset,
        "semana_anterior": offset - 1,
        "semana_siguiente": offset + 1,
        "es_semana_actual": offset == 0,
        "pendientes": pendientes_de_la_semana(request.user, referencia),
        "semana": resumen_semana(request.user, referencia),
        "estado": estado_plan(request.user),
    }
    return render(request, "residencias/agenda.html", contexto)


def residencia_list(request):
    busqueda = request.GET.get("q", "").strip()
    residencias = Residencia.objects.filter(
        propietario=request.user, activo=True
    ).select_related("zona")
    if busqueda:
        residencias = residencias.filter(
            Q(nombre__icontains=busqueda)
            | Q(direccion__icontains=busqueda)
            | Q(telefono__icontains=busqueda)
            | Q(zona__nombre__icontains=busqueda)
        )
    activas = residencias.count()
    return render(
        request,
        "residencias/residencia_list.html",
        {
            "residencias": residencias,
            "q": busqueda,
            "activas": activas,
            "estado": estado_plan(request.user),
        },
    )


def residencia_form(request, pk=None):
    residencia = (
        get_object_or_404(Residencia, pk=pk, propietario=request.user)
        if pk
        else None
    )
    estado = estado_plan(request.user)
    if not residencia and not estado["puede_agregar"]:
        messages.error(
            request,
            f"Tu plan gratis permite {estado['limite_residencias']} residencias. "
            "Pasa a Pro para aÃ±adir mÃ¡s.",
        )
        return redirect("planes")
    if request.method == "POST":
        form = ResidenciaForm(request.POST, instance=residencia, user=request.user)
        if form.is_valid():
            guardada = form.save(commit=False)
            guardada.propietario = request.user
            guardada.save()
            messages.success(request, f"Residencia Â«{guardada.nombre}Â» guardada.")
            return redirect("residencia_detalle", pk=guardada.pk)
    else:
        form = ResidenciaForm(instance=residencia, user=request.user)
    return render(
        request,
        "residencias/residencia_form.html",
        {"form": form, "residencia": residencia, "estado": estado},
    )


def residencia_detalle(request, pk):
    residencia = get_object_or_404(
        Residencia.objects.select_related("zona"),
        pk=pk,
        propietario=request.user,
    )
    inicio, fin = rango_semana()
    visitas = list(
        residencia.visitas.select_related("residencia").prefetch_related(
            "lineas__producto"
        )[:40]
    )
    contexto = {
        "residencia": residencia,
        "visitas": visitas,
        "hechas_semana": residencia.visitas.filter(
            estado=Visita.Estado.ENTREGADA, fecha__range=(inicio, fin)
        ).count(),
        "inicio_semana": inicio,
        "fin_semana": fin,
    }
    return render(request, "residencias/residencia_detalle.html", contexto)


def residencia_borrar(request, pk):
    residencia = get_object_or_404(
        Residencia, pk=pk, propietario=request.user
    )
    if request.method == "POST":
        try:
            residencia.delete()
            messages.success(request, "Residencia eliminada.")
            return redirect("residencia_list")
        except ProtectedError:
            messages.error(
                request,
                "No se puede borrar: tiene visitas registradas. "
                "DesactÃ­vala para dejar de verla en la agenda.",
            )
            return redirect("residencia_detalle", pk=pk)
    return render(
        request, "residencias/confirmar_borrado.html", {"objeto": residencia}
    )


def zona_list(request):
    zonas = Zona.objects.filter(propietario=request.user).annotate(
        total_residencias=Count("residencias")
    )
    return render(request, "residencias/zona_list.html", {"zonas": zonas})


def zona_form(request, pk=None):
    zona = (
        get_object_or_404(Zona, pk=pk, propietario=request.user) if pk else None
    )
    if request.method == "POST":
        form = ZonaForm(request.POST, instance=zona, user=request.user)
        if form.is_valid():
            guardada = form.save(commit=False)
            guardada.propietario = request.user
            guardada.save()
            messages.success(request, f"Zona Â«{guardada.nombre}Â» guardada.")
            return redirect("zona_list")
    else:
        form = ZonaForm(instance=zona, user=request.user)
    return render(
        request, "residencias/zona_form.html", {"form": form, "zona": zona}
    )


def zona_borrar(request, pk):
    zona = get_object_or_404(Zona, pk=pk, propietario=request.user)
    total = zona.residencias.count()
    if request.method == "POST":
        if total:
            messages.error(
                request,
                "No se puede borrar la zona: todavÃ­a tiene residencias asignadas.",
            )
            return redirect("zona_list")
        nombre = zona.nombre
        zona.delete()
        messages.success(request, f"Zona Â«{nombre}Â» eliminada.")
        return redirect("zona_list")
    return render(
        request,
        "residencias/zona_confirmar_borrado.html",
        {"zona": zona, "total_residencias": total},
    )


def producto_list(request):
    productos = productos_con_stock(request.user, solo_activos=False)
    return render(
        request, "residencias/producto_list.html", {"productos": productos}
    )


def producto_form(request, pk=None):
    producto = (
        get_object_or_404(Producto, pk=pk, propietario=request.user)
        if pk
        else None
    )
    if request.method == "POST":
        form = ProductoForm(request.POST, instance=producto, user=request.user)
        if form.is_valid():
            guardado = form.save(commit=False)
            guardado.propietario = request.user
            guardado.save()
            messages.success(request, f"Producto Â«{guardado.nombre}Â» guardado.")
            return redirect("producto_list")
    else:
        form = ProductoForm(instance=producto, user=request.user)
    return render(
        request,
        "residencias/producto_form.html",
        {"form": form, "producto": producto},
    )


def producto_borrar(request, pk):
    producto = get_object_or_404(Producto, pk=pk, propietario=request.user)
    if request.method == "POST":
        try:
            producto.delete()
            messages.success(request, f"Producto «{producto.nombre}» eliminado.")
            return redirect("producto_list")
        except ProtectedError:
            messages.error(
                request,
                "No se puede borrar el producto: se ha usado en visitas registradas.",
            )
            return redirect("producto_list")
    return render(
        request, "residencias/producto_confirmar_borrado.html", {"objeto": producto}
    )


def cupones(request):
    productos = productos_con_stock(request.user)
    inicio, fin = rango_semana()
    contexto = {
        "productos": productos,
        "total_cupones": sum(p.stock for p in productos),
        "bajos": [p for p in productos if p.bajo],
        "usados_semana": cupones_usados_en(request.user, inicio, fin),
        "movimientos": MovimientoCupon.objects.filter(
            producto__propietario=request.user
        ).select_related("producto")[:20],
        "form": MovimientoCuponForm(
            initial={"fecha": timezone.localdate()}, user=request.user
        ),
    }
    return render(request, "residencias/cupones.html", contexto)


def cupon_cargar(request):
    if request.method == "POST":
        form = MovimientoCuponForm(request.POST, user=request.user)
        if form.is_valid():
            movimiento = form.save()
            messages.success(
                request,
                f"{movimiento.cantidad:+d} cupones de Â«{movimiento.producto.nombre}Â».",
            )
        else:
            for errores in form.errors.values():
                messages.error(request, errores[0])
    return redirect("cupones")


def visita_form(request, pk=None):
    visita = (
        get_object_or_404(Visita, pk=pk, residencia__propietario=request.user)
        if pk
        else None
    )
    if request.method == "POST":
        form = VisitaForm(request.POST, instance=visita, user=request.user)
        formset = VisitaProductoFormSet(
            request.POST, instance=visita, form_kwargs={"user": request.user}
        )
        if form.is_valid() and formset.is_valid():
            guardada = form.save()
            formset.instance = guardada
            formset.save()
            messages.success(request, "Visita guardada.")
            return redirect("visita_detalle", pk=guardada.pk)
        messages.error(request, "Revisa los datos de la visita.")
    else:
        initial = {}
        residencia_id = request.GET.get("residencia")
        if residencia_id and not visita:
            initial["residencia"] = residencia_id
        form = VisitaForm(instance=visita, initial=initial, user=request.user)
        formset = VisitaProductoFormSet(
            instance=visita, form_kwargs={"user": request.user}
        )
    productos_cupones = {
        str(p.pk): p.cupones_por_unidad
        for p in Producto.objects.filter(
            propietario=request.user, activo=True
        )
    }
    return render(
        request,
        "residencias/visita_form.html",
        {
            "form": form,
            "formset": formset,
            "visita": visita,
            "productos_cupones": productos_cupones,
        },
    )


def visita_detalle(request, pk):
    visita = get_object_or_404(
        Visita.objects.select_related(
            "residencia", "residencia__zona"
        ).prefetch_related("lineas__producto"),
        pk=pk,
        residencia__propietario=request.user,
    )
    return render(
        request, "residencias/visita_detalle.html", {"visita": visita}
    )


def visita_estado(request, pk, estado):
    visita = get_object_or_404(
        Visita, pk=pk, residencia__propietario=request.user
    )
    if request.method == "POST":
        if estado in dict(Visita.Estado.choices):
            visita.estado = estado
            visita.save(update_fields=["estado", "actualizado_en"])
            messages.success(
                request,
                f"{visita.residencia.nombre}: {visita.get_estado_display()}.",
            )
        else:
            messages.error(request, "Estado no vÃ¡lido.")
    return redirect("agenda")


def visita_borrar(request, pk):
    visita = get_object_or_404(
        Visita, pk=pk, residencia__propietario=request.user
    )
    if request.method == "POST":
        visita.delete()
        messages.success(request, "Visita eliminada.")
        return redirect("agenda")
    return render(
        request, "residencias/confirmar_borrado.html", {"objeto": visita}
    )


def rangos_del_mes(mes):
    try:
        anio, numero = [int(parte) for parte in mes.split("-")]
        inicio = date(anio, numero, 1)
    except (ValueError, AttributeError):
        inicio = timezone.localdate().replace(day=1)
    if inicio.month == 12:
        siguiente = date(inicio.year + 1, 1, 1)
    else:
        siguiente = date(inicio.year, inicio.month + 1, 1)
    fin = siguiente - timedelta(days=1)
    return inicio, fin, siguiente


def datos_reporte_mensual(request):
    hoy = timezone.localdate()
    mes = request.GET.get("mes") or hoy.strftime("%Y-%m")
    inicio, fin, siguiente = rangos_del_mes(mes)
    residencia_id = request.GET.get("residencia") or ""

    residencias = Residencia.objects.filter(
        propietario=request.user
    ).order_by("zona__orden", "orden_ruta", "nombre")
    visitas = (
        Visita.objects.filter(
            residencia__propietario=request.user,
            estado=Visita.Estado.ENTREGADA,
            fecha__range=(inicio, fin),
        )
        .select_related("residencia", "residencia__zona")
        .prefetch_related("lineas__producto")
        .order_by("fecha", "turno", "residencia__nombre")
    )
    if residencia_id:
        visitas = visitas.filter(residencia_id=residencia_id)

    filas = []
    por_residencia = {}
    por_producto = {}
    total_unidades = 0
    total_cupones = 0
    for visita in visitas:
        unidades = visita.total_unidades
        cupones = visita.total_cupones
        total_unidades += unidades
        total_cupones += cupones
        filas.append(
            {"visita": visita, "unidades": unidades, "cupones": cupones}
        )
        resumen = por_residencia.setdefault(
            visita.residencia_id,
            {
                "residencia": visita.residencia,
                "visitas": 0,
                "unidades": 0,
                "cupones": 0,
            },
        )
        resumen["visitas"] += 1
        resumen["unidades"] += unidades
        resumen["cupones"] += cupones
        for linea in visita.lineas.all():
            producto = por_producto.setdefault(
                linea.producto_id,
                {"producto": linea.producto, "cantidad": 0, "cupones": 0},
            )
            producto["cantidad"] += linea.cantidad
            producto["cupones"] += linea.cupones

    contexto = {
        "mes": inicio.strftime("%Y-%m"),
        "mes_anterior": (inicio - timedelta(days=1)).strftime("%Y-%m"),
        "mes_siguiente": siguiente.strftime("%Y-%m"),
        "inicio": inicio,
        "fin": fin,
        "filas": filas,
        "residencias": residencias,
        "residencia_id": residencia_id,
        "por_residencia": sorted(
            por_residencia.values(), key=lambda r: r["residencia"].nombre
        ),
        "por_producto": sorted(
            por_producto.values(), key=lambda p: p["producto"].nombre
        ),
        "total_visitas": len(filas),
        "total_unidades": total_unidades,
        "total_cupones": total_cupones,
        "perfil": perfil_de(request.user),
        "es_mes_actual": inicio.strftime("%Y-%m") == hoy.strftime("%Y-%m"),
    }
    return contexto


def reporte_mensual(request):
    return render(
        request,
        "residencias/reporte_mensual.html",
        datos_reporte_mensual(request),
    )


def reporte_mensual_pdf(request):
    from io import BytesIO

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    datos = datos_reporte_mensual(request)
    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        title=f"Informe mensual {datos['mes']}",
    )
    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle(
        "titulo", parent=estilos["Title"], fontSize=17, spaceAfter=2
    )
    subtitulo = ParagraphStyle(
        "subtitulo",
        parent=estilos["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#475569"),
    )
    seccion = ParagraphStyle(
        "seccion",
        parent=estilos["Heading2"],
        fontSize=12,
        spaceBefore=14,
        spaceAfter=6,
        textColor=colors.HexColor("#0f766e"),
    )
    celda = ParagraphStyle(
        "celda", parent=estilos["Normal"], fontSize=8, leading=10
    )
    cabecera_celda = ParagraphStyle(
        "cabecera_celda",
        parent=celda,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    perfil = datos["perfil"]
    empresa = (
        perfil.empresa or request.user.get_full_name() or request.user.username
    )
    contacto = " Â· ".join(
        valor
        for valor in [
            perfil.cif,
            perfil.telefono,
            perfil.email_contacto,
            perfil.direccion,
        ]
        if valor
    )

    elementos = [Paragraph(empresa, titulo)]
    if contacto:
        elementos.append(Paragraph(contacto, subtitulo))
    elementos.append(Spacer(1, 8))
    elementos.append(Paragraph("Informe mensual de entregas", estilos["Heading1"]))
    elementos.append(
        Paragraph(
            f"Del {datos['inicio']:%d/%m/%Y} al {datos['fin']:%d/%m/%Y}",
            subtitulo,
        )
    )
    elementos.append(
        Paragraph(
            f"Generado el {timezone.localdate():%d/%m/%Y} Â· Ruta Residencias",
            subtitulo,
        )
    )
    elementos.append(Spacer(1, 12))

    resumen = [
        ["Residencias", "Visitas", "Unidades", "Cupones"],
        [
            str(len(datos["por_residencia"])),
            str(datos["total_visitas"]),
            str(datos["total_unidades"]),
            str(datos["total_cupones"]),
        ],
    ]
    tabla_resumen = Table(resumen, colWidths=[4.4 * cm] * 4)
    tabla_resumen.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 1), (-1, 1), 14),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elementos.append(tabla_resumen)

    

    if datos["por_residencia"]:
        elementos.append(Paragraph("Resumen por residencia", seccion))
        filas = [
            [
                Paragraph("Residencia", cabecera_celda),
                Paragraph("Visitas", cabecera_celda),
                Paragraph("Unidades", cabecera_celda),
                Paragraph("Cupones", cabecera_celda),
            ]
        ]
        for resumen_residencia in datos["por_residencia"]:
            filas.append(
                [
                    Paragraph(resumen_residencia["residencia"].nombre, celda),
                    Paragraph(str(resumen_residencia["visitas"]), celda),
                    Paragraph(str(resumen_residencia["unidades"]), celda),
                    Paragraph(str(resumen_residencia["cupones"]), celda),
                ]
            )
        filas.append(
            [
                Paragraph("Totales", celda),
                Paragraph(str(sum(r["visitas"] for r in datos["por_residencia"])), celda),
                Paragraph(str(sum(r["unidades"] for r in datos["por_residencia"])), celda),
                Paragraph(str(sum(r["cupones"] for r in datos["por_residencia"])), celda),
            ]
        )
        tabla = Table(filas, colWidths=[9.4 * cm, 2.2 * cm, 2.2 * cm, 2.2 * cm], repeatRows=1)
        tabla.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elementos.append(tabla)

    def pie(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(1.6 * cm, 1.1 * cm, "Ruta Residencias")
        canvas.drawRightString(
            A4[0] - 1.6 * cm, 1.1 * cm, f"PÃ¡gina {doc.page}"
        )
        canvas.restoreState()

    documento.build(elementos, onFirstPage=pie, onLaterPages=pie)
    respuesta = HttpResponse(
        buffer.getvalue(), content_type="application/pdf"
    )
    respuesta["Content-Disposition"] = (
        f'inline; filename="informe-entregas-{datos["mes"]}.pdf"'
    )
    return respuesta


