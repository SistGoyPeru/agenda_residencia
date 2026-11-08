from datetime import timedelta

from django.contrib import messages
from django.db.models import Count, ProtectedError, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    MovimientoCuponForm,
    ProductoForm,
    ResidenciaForm,
    VisitaForm,
    VisitaProductoFormSet,
)
from .models import (
    MovimientoCupon,
    Producto,
    Residencia,
    Visita,
    VisitaProducto,
    dia_semana_de,
    rango_semana,
    siguiente_residencia,
)


def productos_con_stock(solo_activos=True):
    """Lista de productos con las cifras de cupones ya calculadas."""
    queryset = Producto.objects.all()
    if solo_activos:
        queryset = queryset.filter(activo=True)
    productos = list(queryset)

    cargados = {
        fila["producto_id"]: fila["total"]
        for fila in MovimientoCupon.objects.values("producto_id").annotate(
            total=Sum("cantidad")
        )
    }
    usados = {
        fila["producto_id"]: fila["total"]
        for fila in VisitaProducto.objects.filter(
            visita__estado=Visita.Estado.ENTREGADA
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


def cupones_usados_en(inicio, fin):
    return (
        VisitaProducto.objects.filter(
            visita__estado=Visita.Estado.ENTREGADA,
            visita__fecha__range=(inicio, fin),
        ).aggregate(total=Sum("cupones"))["total"]
        or 0
    )


def pendientes_de_la_semana(referencia):
    """Residencias a las que aún les faltan visitas esta semana."""
    inicio, fin = rango_semana(referencia)
    entregadas = {
        fila["residencia_id"]: fila["total"]
        for fila in Visita.objects.filter(
            estado=Visita.Estado.ENTREGADA, fecha__range=(inicio, fin)
        )
        .values("residencia_id")
        .annotate(total=Count("id"))
    }
    dia_hoy = dia_semana_de(referencia)
    filas = []
    for residencia in Residencia.objects.filter(activo=True).select_related("zona"):
        hechas = entregadas.get(residencia.pk, 0)
        faltan = residencia.frecuencia_semanal - hechas
        if faltan > 0:
            filas.append(
                {"residencia": residencia, "hechas": hechas, "faltan": faltan}
            )
    filas.sort(
        key=lambda fila: (
            0 if fila["residencia"].dia_preferido == dia_hoy else 1,
            fila["residencia"].zona.orden if fila["residencia"].zona else 999,
            fila["residencia"].orden_ruta,
            fila["residencia"].nombre,
        )
    )
    return filas


def dashboard(request):
    hoy = timezone.localdate()
    inicio, fin = rango_semana(hoy)
    visitas_hoy = list(
        Visita.objects.filter(fecha=hoy)
        .select_related("residencia", "residencia__zona")
        .order_by("turno", "residencia__zona__orden", "residencia__orden_ruta")
    )
    resumen_hoy = {
        "total": len(visitas_hoy),
        "entregadas": sum(v.estado == Visita.Estado.ENTREGADA for v in visitas_hoy),
        "pendientes": sum(v.estado == Visita.Estado.PENDIENTE for v in visitas_hoy),
        "incidencias": sum(v.estado == Visita.Estado.INCIDENCIA for v in visitas_hoy),
    }
    productos = productos_con_stock()
    contexto = {
        "hoy": hoy,
        "visitas_hoy": visitas_hoy,
        "resumen_hoy": resumen_hoy,
        "siguiente": siguiente_residencia(hoy),
        "pendientes": pendientes_de_la_semana(hoy),
        "productos_bajos": [p for p in productos if p.bajo],
        "productos": productos,
        "cupones_semana": cupones_usados_en(inicio, fin),
        "total_cupones": sum(p.stock for p in productos),
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
            Visita.objects.filter(fecha=dia)
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
        "pendientes": pendientes_de_la_semana(referencia),
    }
    return render(request, "residencias/agenda.html", contexto)


def residencia_list(request):
    busqueda = request.GET.get("q", "").strip()
    residencias = Residencia.objects.filter(activo=True).select_related("zona")
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
        {"residencias": residencias, "q": busqueda, "activas": activas},
    )


def residencia_form(request, pk=None):
    residencia = get_object_or_404(Residencia, pk=pk) if pk else None
    if request.method == "POST":
        form = ResidenciaForm(request.POST, instance=residencia)
        if form.is_valid():
            guardada = form.save()
            messages.success(request, f"Residencia «{guardada.nombre}» guardada.")
            return redirect("residencia_detalle", pk=guardada.pk)
    else:
        form = ResidenciaForm(instance=residencia)
    return render(
        request,
        "residencias/residencia_form.html",
        {"form": form, "residencia": residencia},
    )


def residencia_detalle(request, pk):
    residencia = get_object_or_404(
        Residencia.objects.select_related("zona"), pk=pk
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
    residencia = get_object_or_404(Residencia, pk=pk)
    if request.method == "POST":
        try:
            residencia.delete()
            messages.success(request, "Residencia eliminada.")
            return redirect("residencia_list")
        except ProtectedError:
            messages.error(
                request,
                "No se puede borrar: tiene visitas registradas. "
                "Desactívala para dejar de verla en la agenda.",
            )
            return redirect("residencia_detalle", pk=pk)
    return render(
        request, "residencias/confirmar_borrado.html", {"objeto": residencia}
    )


def producto_list(request):
    productos = productos_con_stock(solo_activos=False)
    return render(
        request, "residencias/producto_list.html", {"productos": productos}
    )


def producto_form(request, pk=None):
    producto = get_object_or_404(Producto, pk=pk) if pk else None
    if request.method == "POST":
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            guardado = form.save()
            messages.success(request, f"Producto «{guardado.nombre}» guardado.")
            return redirect("producto_list")
    else:
        form = ProductoForm(instance=producto)
    return render(
        request,
        "residencias/producto_form.html",
        {"form": form, "producto": producto},
    )


def cupones(request):
    productos = productos_con_stock()
    inicio, fin = rango_semana()
    contexto = {
        "productos": productos,
        "total_cupones": sum(p.stock for p in productos),
        "bajos": [p for p in productos if p.bajo],
        "usados_semana": cupones_usados_en(inicio, fin),
        "movimientos": MovimientoCupon.objects.select_related("producto")[:20],
        "form": MovimientoCuponForm(initial={"fecha": timezone.localdate()}),
    }
    return render(request, "residencias/cupones.html", contexto)


def cupon_cargar(request):
    if request.method == "POST":
        form = MovimientoCuponForm(request.POST)
        if form.is_valid():
            movimiento = form.save()
            messages.success(
                request,
                f"{movimiento.cantidad:+d} cupones de «{movimiento.producto.nombre}».",
            )
        else:
            for errores in form.errors.values():
                messages.error(request, errores[0])
    return redirect("cupones")


def visita_form(request, pk=None):
    visita = get_object_or_404(Visita, pk=pk) if pk else None
    if request.method == "POST":
        form = VisitaForm(request.POST, instance=visita)
        formset = VisitaProductoFormSet(request.POST, instance=visita)
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
        form = VisitaForm(instance=visita, initial=initial)
        formset = VisitaProductoFormSet(instance=visita)
    productos_cupones = {
        str(p.pk): p.cupones_por_unidad
        for p in Producto.objects.filter(activo=True)
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
        Visita.objects.select_related("residencia", "residencia__zona").prefetch_related(
            "lineas__producto"
        ),
        pk=pk,
    )
    return render(
        request, "residencias/visita_detalle.html", {"visita": visita}
    )


def visita_estado(request, pk, estado):
    visita = get_object_or_404(Visita, pk=pk)
    if request.method == "POST":
        if estado in dict(Visita.Estado.choices):
            visita.estado = estado
            visita.save(update_fields=["estado", "actualizado_en"])
            messages.success(
                request,
                f"{visita.residencia.nombre}: {visita.get_estado_display()}.",
            )
        else:
            messages.error(request, "Estado no válido.")
    return redirect("visita_detalle", pk=pk)


def visita_borrar(request, pk):
    visita = get_object_or_404(Visita, pk=pk)
    if request.method == "POST":
        visita.delete()
        messages.success(request, "Visita eliminada.")
        return redirect("agenda")
    return render(
        request, "residencias/confirmar_borrado.html", {"objeto": visita}
    )
